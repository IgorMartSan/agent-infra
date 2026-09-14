import logging
from datetime import datetime, timezone
from typing import Any, List, Dict

from pymongo.collection import Collection

logger = logging.getLogger(__name__)


class ShortTermRepository:
    def __init__(
        self,
        mongo_connection,
        collection_name: str = "messages",
        max_messages: int = 200,
    ):
        self.collection: Collection = mongo_connection.get_database()[collection_name]
        self.max_messages = max_messages

        self._create_indexes()

    def _create_indexes(self):
        self.collection.create_index([("client_id", 1), ("created_at", -1)])

    # ==========================================================
    # 🔹 SAVE (USER + LLM)
    # ==========================================================
    def save(
        self,
        platform: str,
        user_id: str,
        message: str,
        role: str,  # "user" | "assistant"
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        try:
            now = datetime.now(timezone.utc)
            client_id = f"{platform}:{user_id}"

            doc = {
                "client_id": client_id,
                "platform": platform,
                "platform_user_id": user_id,
                "message": message,
                "role": role,
                "metadata": metadata or {},
                "created_at": now,
            }

            self.collection.insert_one(doc)

            # 🔥 controle de tamanho
            self._enforce_limit(client_id)

        except Exception:
            logger.exception("Erro ao salvar mensagem")
            raise

    # ==========================================================
    # 🔹 LIMITE (OTIMIZADO)
    # ==========================================================
    def _enforce_limit(self, client_id: str) -> None:
        """
        Mantém apenas as últimas N mensagens.

        🔥 Otimizado:
        - evita count completo sempre que possível
        """
        try:
            # pega só o excedente
            cursor = (
                self.collection.find({"client_id": client_id})
                .sort("created_at", -1)
                .skip(self.max_messages)
                .limit(100)  # segurança
            )

            ids_to_delete = [doc["_id"] for doc in cursor]

            if ids_to_delete:
                self.collection.delete_many({"_id": {"$in": ids_to_delete}})

        except Exception:
            logger.exception("Erro ao controlar limite")

    # ==========================================================
    # 🔹 GET RECENT (PRONTO PRA LLM)
    # ==========================================================
    def get_recent(
        self,
        client_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        try:
            cursor = (
                self.collection.find({"client_id": client_id})
                .sort("created_at", -1)
                .limit(limit)
            )

            # 🔥 formato ideal pra LLM
            return [
                {
                    "role": doc["role"],
                    "content": doc["message"],
                }
                for doc in reversed(list(cursor))
            ]

        except Exception:
            logger.exception("Erro ao buscar mensagens")
            raise

    # ==========================================================
    # 🔹 CONTAGEM
    # ==========================================================
    def count(self, client_id: str) -> int:
        return self.collection.count_documents({"client_id": client_id})

    # ==========================================================
    # 🔹 GET RAW (debug / análise)
    # ==========================================================
    def get_recent_raw(
        self,
        client_id: str,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        try:
            return list(
                self.collection.find({"client_id": client_id})
                .sort("created_at", -1)
                .limit(limit)
            )
        except Exception:
            logger.exception("Erro ao buscar mensagens raw")
            raise