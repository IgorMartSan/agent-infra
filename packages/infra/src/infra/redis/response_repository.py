import json
import logging
from urllib.parse import quote

from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class ChatResponsePubSubRepository:
    """Publica respostas de chat em canais Redis Pub/Sub."""

    def __init__(self, redis_connection, channel_prefix: str = "chat:response"):
        self.redis: Redis = redis_connection.get_client()
        self.channel_prefix = channel_prefix

    def channel_name(self, user_id: str, chat_id: str) -> str:
        user_key = quote(user_id, safe="")
        chat_key = quote(chat_id, safe="")
        return f"{self.channel_prefix}:{user_key}:{chat_key}"

    async def publish_response(
        self,
        *,
        user_id: str,
        chat_id: str,
        batch_id: str | int,
        response: str,
        agent_id: str | None = None,
    ) -> int:
        try:
            payload_data = {
                "user_id": user_id,
                "chat_id": chat_id,
                "batch_id": batch_id,
                "response": response,
            }
            if agent_id:
                payload_data["agent_id"] = agent_id

            return int(
                await self.redis.publish(
                    self.channel_name(user_id, chat_id),
                    json.dumps(payload_data, ensure_ascii=False),
                )
            )
        except RedisError:
            logger.exception("Erro ao publicar resposta no Redis")
            raise
