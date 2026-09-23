"""Worker de produção do Agente Unificado — fluxo: RabbitMQ -> agente MCP -> Redis Pub/Sub.

A configuração do agente (ID, filas, MCP server) é lida inteiramente do .env,
permitindo que este mesmo código sirva múltiplos agentes apenas trocando o ambiente.

Estrutura do fluxo (visível em 5 passos dentro de handle_message):
1. O consumer entrega o payload recebido do RabbitMQ.
2. O processor valida o payload e roda o agente (LangGraph + MCP tools).
3. A resposta é publicada no Redis Pub/Sub no canal da conversa.
4. O ACK confirma o processamento ao RabbitMQ.
5. Se algo falhar, o consumer decide reprocessar ou descartar.
"""

import logging
import os
import time

from dotenv import load_dotenv

from infra.rabbitmq.connection import RabbitMQConnection
from infra.rabbitmq.consumer import RabbitMQConsumer
from infra.redis import (
    AgentRegistry,
    AgentResponsePubSubRepository,
    ConversationLock,
    RedisConnection,
)
from processor import AgentProcessingError, InvalidMessageError, process_agent_message

load_dotenv()

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def build_response_publisher() -> AgentResponsePubSubRepository:
    """Cria o publicador de respostas no Redis Pub/Sub (passo 3)."""
    return AgentResponsePubSubRepository(
        RedisConnection(),
        channel_prefix=os.environ["REDIS_RESPONSE_CHANNEL_PREFIX"],
    )


def run_worker() -> None:
    agent_id = os.environ["AGENT_ID"]
    exchange = os.environ["RABBITMQ_EXCHANGE"]
    queue = os.environ["RABBITMQ_QUEUE"]
    routing_key = os.environ["RABBITMQ_ROUTING_KEY"]
    prefetch_count = int(os.environ["RABBITMQ_PREFETCH_COUNT"])
    reconnect_delay = float(os.environ["RABBITMQ_RECONNECT_DELAY"])

    redis_connection = RedisConnection()
    response_pubsub = build_response_publisher()
    conversation_lock = ConversationLock(redis_connection.get_client())

    agent_registry = AgentRegistry(
        redis_connection.get_client(),
        agent_id,
        ttl_seconds=int(os.environ.get("AGENT_HEARTBEAT_TTL_SECONDS", "30")),
        interval_seconds=float(
            os.environ.get("AGENT_HEARTBEAT_INTERVAL_SECONDS", "10")
        ),
    )
    agent_registry.start()

    logger.info(
        "Agente unificado iniciado: agent_id=%s queue=%s mcp_server=%s",
        agent_id,
        queue,
        os.getenv("MCP_SERVER_PATH", "não configurado"),
    )

    def release_lock(payload: dict) -> None:
        """Libera a conversa para a próxima mensagem."""
        try:
            conversation_lock.release(
                application_id=payload.get("application_id"),
                chat_id=payload.get("chat_id"),
                agent_id=payload.get("agent_id"),
            )
        except Exception:
            logger.exception(
                "Não foi possível liberar o lock da conversa: message_id=%s",
                payload.get("message_id", "sem-id"),
            )

    def publish_error(payload: dict, reason: str) -> None:
        """Publica o evento de falha no canal da conversa."""
        conversation_id = payload.get("conversation_id") or payload.get("chat_id")
        try:
            subscribers = response_pubsub.publish_failed(
                application_id=payload.get("application_id"),
                conversation_id=conversation_id,
                message_id=payload.get("message_id"),
                agent_id=payload.get("agent_id"),
                reason=reason,
            )
            logger.info(
                "Falha notificada ao cliente: message_id=%s redis_subscribers=%s",
                payload.get("message_id", "sem-id"),
                subscribers,
            )
        except Exception:
            logger.exception(
                "Não foi possível notificar o cliente da falha: message_id=%s",
                payload.get("message_id", "sem-id"),
            )

    def handle_message(payload: dict) -> None:
        """Passos 1 a 3 do fluxo, executados para cada mensagem consumida."""
        try:
            response = process_agent_message(payload)
        except AgentProcessingError as error:
            publish_error(payload, str(error))
            release_lock(payload)
            raise

        conversation_id = payload.get("conversation_id") or payload.get("chat_id")
        subscribers = response_pubsub.publish_completed(
            application_id=payload.get("application_id"),
            conversation_id=conversation_id,
            message_id=payload.get("message_id"),
            agent_id=payload.get("agent_id"),
            content=response["response"],
        )
        logger.info(
            "Mensagem processada: message_id=%s redis_subscribers=%s",
            payload.get("message_id", "sem-id"),
            subscribers,
        )
        release_lock(payload)

    try:
        while True:
            connection = RabbitMQConnection()
            consumer = RabbitMQConsumer(connection)

            try:
                logger.info(
                    "Worker aguardando: agent_id=%s exchange=%s fila=%s routing_key=%s",
                    agent_id,
                    exchange,
                    queue,
                    routing_key,
                )
                consumer.consume(
                    queue=queue,
                    callback=handle_message,
                    exchange=exchange,
                    routing_key=routing_key,
                    prefetch_count=prefetch_count,
                    should_requeue=lambda exc: not isinstance(
                        exc, (InvalidMessageError, AgentProcessingError)
                    ),
                )
            except Exception:
                logger.exception(
                    "Falha no RabbitMQ; nova tentativa em %.1f segundo(s).",
                    reconnect_delay,
                )
                time.sleep(reconnect_delay)
            finally:
                connection.close()

    except KeyboardInterrupt:
        logger.info("Worker encerrado pelo usuário.")
    finally:
        agent_registry.stop()
        redis_connection.close()


if __name__ == "__main__":
    run_worker()