import logging
import os
import time

from dotenv import load_dotenv

from infra.rabbitmq.connection import RabbitMQConnection
from infra.rabbitmq.consumer import RabbitMQConsumer
from infra.rabbitmq.producer import RabbitMQProducer
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
    outbound_queue = os.getenv("RABBITMQ_OUTBOUND_QUEUE", "agent.outbound")
    prefetch_count = int(os.getenv("RABBITMQ_PREFETCH_COUNT", "1"))
    reconnect_delay = float(os.getenv("RABBITMQ_RECONNECT_DELAY", "3"))

    try:
        while True:
            connection = RabbitMQConnection()
            producer = RabbitMQProducer(connection)
            consumer = RabbitMQConsumer(connection)

            def handle_message(payload: dict) -> None:
                response = process_agent_message(payload)
                producer.publish(queue=outbound_queue, message=response)
                logger.info(
                    "Mensagem processada: message_id=%s fila_resposta=%s",
                    payload.get("message_id", "sem-id"),
                    outbound_queue,
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


if __name__ == "__main__":
    main()
