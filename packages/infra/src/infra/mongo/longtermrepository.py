import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)


class LongTermRepository:
    def __init__(
        self,
        mongo_connection,
        collection_name: str = "contexts",
    ):
        self.collection = mongo_connection.get_database()[collection_name]
        self._create_indexes()

    def _create_indexes(self):
        self.collection.create_index("client_id", unique=True)

    def get(self, client_id: str) -> dict | None:
        try:
            return self.collection.find_one({"client_id": client_id}, {"_id": 0})
        except Exception:
            logger.exception("Erro ao buscar contexto")
            raise

    def upsert_context(
        self,
        client_id: str,
        context_type: str,
        data: dict[str, Any],
    ):
        try:
            now = datetime.now(timezone.utc)

            self.collection.update_one(
                {"client_id": client_id},
                {
                    "$set": {
                        f"contexts.{context_type}": data,
                        "updated_at": now,
                    },
                    "$setOnInsert": {
                        "client_id": client_id,
                        "created_at": now,
                    },
                },
                upsert=True,
            )

        except Exception:
            logger.exception("Erro ao salvar contexto")
            raise