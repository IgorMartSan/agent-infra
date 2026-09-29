"""Worker: RabbitMQ -> agente -> Redis Pub/Sub."""

import logging
import os
import time

from config.logger import setup_logger
from dotenv import load_dotenv

from agents.langchain_agents.agent_runtime import AgentProcessingError, get_agent
from infra.rabbitmq.connection import RabbitMQConnection
from infra.redis.agent_registry import AgentRegistry
from infra.redis.connection import RedisConnection
from infra.redis.conversation_lock import ConversationLock
from infra.redis.response_repository import AgentResponsePubSubRepository


logger = logging.getLogger(__name__)


def main():
    load_dotenv()
    setup_logger("INFO")

    agent_id = os.environ["AGENT_ID"]

    queue = (
        f"agent."
        f"{agent_id.removesuffix('-agent').replace('-', '.')}"
        f".requests"
    )

    redis = RedisConnection()

    heartbeat = AgentRegistry(
        redis.get_client(),
        agent_id,
    )

    publisher = AgentResponsePubSubRepository(
        redis
    )

    conversation_lock = ConversationLock(
        redis.get_client()
    )

    try:
        with get_agent(agent_id) as agent:
            while True:
                rabbitmq = RabbitMQConnection()

                try:
                    messages = rabbitmq.consume(queue)

                    heartbeat.start()

                    logger.info(
                        "Worker aguardando mensagens: queue=%s",
                        queue,
                    )

                    for message in messages:
                        try:
                            response = agent.invoke(message)
                            failed = False

                        except AgentProcessingError as error:
                            logger.exception(
                                "Falha do agente: message_id=%s",
                                message.message_id,
                            )

                            response = str(error)
                            failed = True

                        subscribers = publisher.publish(
                            message,
                            response,
                            failed=failed,
                        )

                        conversation_lock.release(
                            message.application_id,
                            message.chat_id,
                            message.agent_id,
                        )

                        rabbitmq.ack()

                        logger.info(
                            "Resposta publicada: "
                            "message_id=%s subscribers=%s",
                            message.message_id,
                            subscribers,
                        )

                except Exception:
                    logger.exception(
                        "Falha no consumo; reconectando "
                        "ao RabbitMQ em 3 segundos."
                    )

                finally:
                    heartbeat.stop()
                    rabbitmq.close()

                time.sleep(3)

    except KeyboardInterrupt:
        logger.info("Worker encerrado.")

    finally:
        redis.close()


if __name__ == "__main__":
    main()
