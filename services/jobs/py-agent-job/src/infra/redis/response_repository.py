import json
import logging
from urllib.parse import quote

from redis import Redis
from redis.exceptions import RedisError

from entity.message import AgentMessage

logger = logging.getLogger(__name__)


class AgentResponsePubSubRepository:
    """Publica o evento final do agente em um canal Redis Pub/Sub."""

    def __init__(self, redis_connection) -> None:
        self._redis: Redis = redis_connection.get_client()

    def publish(self, message: AgentMessage, content: str, *, failed: bool = False) -> int:
        """Publica a resposta ou o erro com os IDs recebidos na mensagem."""
        channel = f"chat:response:{quote(message.application_id, safe='')}"
        if message.chat_id:
            channel += f":{quote(message.chat_id, safe='')}"
        event = {
            "type": "message.failed" if failed else "message.completed",
            "application_id": message.application_id,
            "conversation_id": message.chat_id,
            "message_id": message.message_id,
            "agent_id": message.agent_id,
            "content": content,
        }
        try:
            return int(self._redis.publish(channel, json.dumps(event, ensure_ascii=False)))
        except RedisError:
            logger.exception("Erro ao publicar evento no Redis Pub/Sub")
            raise
