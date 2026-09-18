import logging
import os
import time

from dotenv import load_dotenv

from infra.rabbitmq.connection import RabbitMQConnection
from infra.rabbitmq.consumer import RabbitMQConsumer
from infra.redis import AgentRegistry, AgentResponsePubSubRepository, ConversationLock, RedisConnection
from processor import InvalidMessageError, process_agent_message

load_dotenv()

logging.basicConfig(
    level=os.environ["LOG_LEVEL"].upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    agent_id = os.environ["AGENT_ID"]
    exchange = os.environ["RABBITMQ_EXCHANGE"]
    queue = os.environ["RABBITMQ_QUEUE"]
    routing_key = os.environ["RABBITMQ_ROUTING_KEY"]
    prefetch_count = int(os.environ["RABBITMQ_PREFETCH_COUNT"])
    reconnect_delay = float(os.environ["RABBITMQ_RECONNECT_DELAY"])
    redis_connection = RedisConnection()
    response_pubsub = AgentResponsePubSubRepository(
        redis_connection,
        channel_prefix=os.environ["REDIS_RESPONSE_CHANNEL_PREFIX"],
    )
    conversation_lock = ConversationLock(redis_connection.get_client())

    try:
        while True:
            connection = RabbitMQConnection()
            consumer = RabbitMQConsumer(connection)
            agent_registry = AgentRegistry(redis_connection.get_client(), agent_id)
            registered = False

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
                conversation_lock.release(
                    application_id=payload["application_id"],
                    chat_id=payload.get("chat_id"),
                    agent_id=payload["agent_id"],
                )

            try:
                connection.connect()
                agent_registry.start()
                registered = True
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
            finally:
                if registered:
                    agent_registry.stop()
                connection.close()
            time.sleep(reconnect_delay)

    except KeyboardInterrupt:
        logger.info("Worker encerrado pelo usuário.")
    finally:
        redis_connection.close()


if __name__ == "__main__":
    main()
