import json
import logging
from urllib.parse import quote

from redis import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class AgentResponsePubSubRepository:
    """Publica o evento final do agente em um canal Redis Pub/Sub."""

    def __init__(
        self,
        redis_connection,
        channel_prefix: str = "chat:response",
    ) -> None:
        self._redis: Redis = redis_connection.get_client()
        self._channel_prefix = channel_prefix

    def channel_name(
        self,
        application_id: str | None,
        conversation_id: str | None,
    ) -> str:
        channel_parts = [self._channel_prefix]

        if application_id:
            channel_parts.append(quote(application_id, safe=""))
        if conversation_id:
            channel_parts.append(quote(conversation_id, safe=""))

        return ":".join(channel_parts)

    def _publish_event(self, event: dict, application_id, conversation_id) -> int:
        try:
            return int(
                self._redis.publish(
                    self.channel_name(application_id, conversation_id),
                    json.dumps(event, ensure_ascii=False),
                )
            )
        except RedisError:
            logger.exception("Erro ao publicar evento no Redis Pub/Sub")
            raise

    def publish_completed(
        self,
        *,
        application_id: str | None,
        conversation_id: str | None,
        message_id: str | None,
        agent_id: str | None,
        content: str,
    ) -> int:
        """Publica o evento final de sucesso no canal da conversa."""
        event = {
            "type": "message.completed",
            "application_id": application_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "agent_id": agent_id,
            "content": content,
        }
        return self._publish_event(event, application_id, conversation_id)

    def publish_failed(
        self,
        *,
        application_id: str | None,
        conversation_id: str | None,
        message_id: str | None,
        agent_id: str | None,
        reason: str,
    ) -> int:
        """Publica o evento de falha no mesmo canal, para o cliente não ficar sem resposta."""
        event = {
            "type": "message.failed",
            "application_id": application_id,
            "conversation_id": conversation_id,
            "message_id": message_id,
            "agent_id": agent_id,
            "content": reason,
        }
        return self._publish_event(event, application_id, conversation_id)
