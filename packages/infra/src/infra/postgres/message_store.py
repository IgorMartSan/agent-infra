from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any

from sqlalchemy import BigInteger, DateTime, Integer, String, Text, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .connection import PostgresConnection


class Base(DeclarativeBase):
    pass


class BatchStatus(StrEnum):
    COLLECTING = "collecting"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"


class ChatBatch(Base):
    __tablename__ = "chat_batches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    chat_id: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(
        String(32), default=BatchStatus.COLLECTING.value, index=True
    )
    messages: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    batch_metadata: Mapped[dict[str, Any] | None] = mapped_column(
        "metadata", JSONB, nullable=True
    )
    final_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_message_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


@dataclass(slots=True)
class BatchAppendResult:
    batch_id: int
    chat_id: str
    status: str
    message_count: int


@dataclass(slots=True)
class BatchForProcessing:
    batch_id: int
    chat_id: str
    messages: list[dict[str, Any]]
    metadata: dict[str, Any] | None
    attempts: int


@dataclass(slots=True)
class ChatHistoryItem:
    chat_id: str
    batch_id: int
    role: str
    content: str
    status: str
    created_at: datetime
    metadata: dict[str, Any] | None = None


class ChatBatchRepository:
    def __init__(self, connection: PostgresConnection) -> None:
        self._connection = connection

    def create_tables(self) -> None:
        Base.metadata.create_all(self._connection.get_engine())

    def append_message(
        self,
        *,
        chat_id: str,
        payload: dict[str, Any],
    ) -> BatchAppendResult:
        now = datetime.now(timezone.utc)

        with self._connection.get_session() as session:
            batch = session.execute(
                select(ChatBatch)
                .where(
                    ChatBatch.chat_id == chat_id,
                    ChatBatch.status == BatchStatus.COLLECTING.value,
                )
                .order_by(ChatBatch.id.asc())
                .limit(1)
                .with_for_update()
            ).scalar_one_or_none()

            if batch is None:
                batch = ChatBatch(
                    chat_id=chat_id,
                    status=BatchStatus.COLLECTING.value,
                    messages=[],
                    batch_metadata=None,
                    final_response=None,
                    attempts=0,
                    created_at=now,
                    updated_at=now,
                    last_message_at=now,
                )
                session.add(batch)
                session.flush()

            batch.messages = [*(batch.messages or []), payload]
            batch.batch_metadata = payload.get("metadata")
            batch.last_message_at = now
            batch.updated_at = now

            session.add(batch)
            session.commit()

            return BatchAppendResult(
                batch_id=batch.id,
                chat_id=batch.chat_id,
                status=batch.status,
                message_count=len(batch.messages or []),
            )

    def claim_collecting_batch(self, *, idle_seconds: int) -> BatchForProcessing | None:
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=idle_seconds)

        with self._connection.get_session() as session:
            batch = session.execute(
                select(ChatBatch)
                .where(
                    ChatBatch.status == BatchStatus.COLLECTING.value,
                    ChatBatch.last_message_at <= cutoff,
                )
                .order_by(ChatBatch.last_message_at.asc(), ChatBatch.id.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            ).scalar_one_or_none()

            if batch is None:
                session.commit()
                return None

            batch.status = BatchStatus.PROCESSING.value
            batch.updated_at = datetime.now(timezone.utc)
            session.commit()

            return BatchForProcessing(
                batch_id=batch.id,
                chat_id=batch.chat_id,
                messages=list(batch.messages or []),
                metadata=batch.batch_metadata,
                attempts=batch.attempts,
            )

    def mark_done(self, batch_id: int, *, final_response: str) -> None:
        with self._connection.get_session() as session:
            batch = session.get(ChatBatch, batch_id)
            if batch is None:
                raise ValueError(f"Batch {batch_id} not found")

            now = datetime.now(timezone.utc)
            batch.status = BatchStatus.DONE.value
            batch.final_response = final_response
            batch.updated_at = now
            session.commit()

    def mark_latest_done_for_chat(self, *, chat_id: str, final_response: str) -> int | None:
        with self._connection.get_session() as session:
            batch = session.execute(
                select(ChatBatch)
                .where(
                    ChatBatch.chat_id == chat_id,
                    ChatBatch.final_response.is_(None),
                )
                .order_by(ChatBatch.last_message_at.desc(), ChatBatch.id.desc())
                .limit(1)
                .with_for_update()
            ).scalar_one_or_none()

            if batch is None:
                session.commit()
                return None

            now = datetime.now(timezone.utc)
            batch.status = BatchStatus.DONE.value
            batch.final_response = final_response
            batch.updated_at = now
            session.commit()
            return batch.id

    def mark_failure(self, batch_id: int, *, max_attempts: int) -> str:
        with self._connection.get_session() as session:
            batch = session.get(ChatBatch, batch_id)
            if batch is None:
                raise ValueError(f"Batch {batch_id} not found")

            now = datetime.now(timezone.utc)
            batch.attempts += 1
            batch.updated_at = now
            batch.last_message_at = now
            batch.status = (
                BatchStatus.ERROR.value
                if batch.attempts >= max_attempts
                else BatchStatus.COLLECTING.value
            )
            session.commit()
            return batch.status

    def list_history(self, *, chat_id: str, limit: int = 50) -> list[ChatHistoryItem]:
        with self._connection.get_session() as session:
            batches = session.execute(
                select(ChatBatch)
                .where(ChatBatch.chat_id == chat_id)
                .order_by(ChatBatch.created_at.asc(), ChatBatch.id.asc())
            ).scalars()

            history: list[ChatHistoryItem] = []

            for batch in batches:
                for payload in batch.messages or []:
                    history.append(
                        ChatHistoryItem(
                            chat_id=batch.chat_id,
                            batch_id=batch.id,
                            role="user",
                            content=str(payload.get("message", "")),
                            status=batch.status,
                            created_at=batch.created_at,
                            metadata=payload.get("metadata"),
                        )
                    )
                    if len(history) >= limit:
                        return history

                if batch.final_response:
                    history.append(
                        ChatHistoryItem(
                            chat_id=batch.chat_id,
                            batch_id=batch.id,
                            role="assistant",
                            content=batch.final_response,
                            status=batch.status,
                            created_at=batch.updated_at,
                        )
                    )
                    if len(history) >= limit:
                        return history

            return history
