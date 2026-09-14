import logging
import os
import time

from dotenv import load_dotenv

from infra.rabbitmq.connection import RabbitMQConnection
from infra.rabbitmq.consumer import RabbitMQConsumer
from infra.redis import AgentResponsePubSubRepository, RedisConnection
from processor import InvalidMessageError, process_agent_message

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    agent_id = os.getenv("AGENT_ID", "simple-agent")
    exchange = os.getenv("RABBITMQ_EXCHANGE", "agent.requests")
    queue = os.getenv("RABBITMQ_QUEUE", "agent.simple.requests")
    routing_key = os.getenv("RABBITMQ_ROUTING_KEY", "agent.simple")
    prefetch_count = int(os.getenv("RABBITMQ_PREFETCH_COUNT", "1"))
    reconnect_delay = float(os.getenv("RABBITMQ_RECONNECT_DELAY", "3"))
    redis_connection = RedisConnection()
    response_pubsub = AgentResponsePubSubRepository(
        redis_connection,
        channel_prefix=os.getenv("REDIS_RESPONSE_CHANNEL_PREFIX", "chat:response"),
    )

    try:
        while True:
            connection = RabbitMQConnection()
            consumer = RabbitMQConsumer(connection)

            def handle_message(payload: dict) -> None:
                response = process_agent_message(payload)

                # A persistência PostgreSQL da resposta será adicionada aqui futuramente.

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
                    should_requeue=lambda exc: not isinstance(exc, InvalidMessageError),
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
        redis_connection.close()


if __name__ == "__main__":
    main()
