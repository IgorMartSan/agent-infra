"""Coordena disponibilidade, limite da fila, lock e publicação."""

import logging

from service.conversation_lock import ConversationLockUnavailable
from service.queue_threshold import QueueOverloaded

logger = logging.getLogger(__name__)


class AgentUnavailable(Exception):
    pass


class MessageUnavailable(Exception):
    pass


def routing_key_for(agent_id):
    name = agent_id.strip().lower().removesuffix("-agent").replace("-", ".")
    return f"agent.{name}"


class MessageService:
    def __init__(self, producer, agents, conversation_lock, queue_threshold, exchange="agent.requests"):
        self._producer = producer
        self._agents = agents
        self._lock = conversation_lock
        self._queue_threshold = queue_threshold
        self._exchange = exchange

    def send(self, message):
        agent_id = message["agent_id"]
        routing_key = routing_key_for(agent_id)
        identity = {
            "application_id": message["application_id"],
            "chat_id": message.get("chat_id"),
            "agent_id": agent_id,
        }
        locked = False
        try:
            if not self._agents.is_available(agent_id):
                raise AgentUnavailable("Não há workers ativos para este agente no momento. Tente novamente mais tarde.")
            self._queue_threshold.check(f"{routing_key}.requests")
            self._lock.acquire(**identity)
            locked = True
            self._producer.publish(exchange=self._exchange, routing_key=routing_key, message=message)
        except (AgentUnavailable, ConversationLockUnavailable, QueueOverloaded):
            raise
        except Exception as error:
            if locked:
                try:
                    self._lock.release(**identity)
                except Exception:
                    logger.exception("Falha ao liberar a conversa; o lock expirará pelo TTL.")
            logger.exception("Falha ao encaminhar message_id=%s", message.get("message_id"))
            raise MessageUnavailable("Infraestrutura indisponível para receber a mensagem.") from error
