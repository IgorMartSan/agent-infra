"""
Worker:
RabbitMQ
   ↓
Agent
   ↓
Redis Pub/Sub
"""

import json
import logging
import os

from dotenv import load_dotenv

from agents.rsa_agent.graph import graph as rsa_graph
from infra.redis.connection import RedisConnection
from infra.rabbitmq.connection import RabbitMQConnection


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(filename)s:%(lineno)d | "
        "%(funcName)s | "
        "%(message)s"
    ),
    datefmt="%Y-%m-%d %H:%M:%S",
)

logger = logging.getLogger(__name__)


# =========================================================
# CONFIGURAÇÕES
# =========================================================

AGENT_ID = os.getenv("AGENT_ID", "rsa-agent")

RABBITMQ_QUEUE = os.getenv("RABBITMQ_QUEUE", "agent.queue")

REDIS_CHANNEL_PREFIX = "chat:response"


# =========================================================
# AGENTES
# =========================================================

AGENTS = {
    "rsa-agent": rsa_graph,
    # Futuramente:
    # "outro-agent": outro_graph,
}


agent = AGENTS.get(AGENT_ID)

if agent is None:
    raise RuntimeError(
        f"Agente '{AGENT_ID}' não encontrado. "
        f"Disponíveis: {list(AGENTS.keys())}"
    )


# =========================================================
# INFRAESTRUTURA
# =========================================================

redis_conn = RedisConnection()
redis_client = redis_conn.get_client()

rabbitmq_conn = RabbitMQConnection()


# =========================================================
# PROCESSAMENTO
# =========================================================

def process_message(payload: dict):

    message = payload.get("message")

    if not message:
        logger.warning("Mensagem vazia")
        return

    logger.info(
        "Processando message_id=%s",
        payload.get("message_id"),
    )

    # Executa o agente LangGraph
    result = agent.invoke({
        "message": message,
        "response": "",
        "thread_id": payload.get("thread_id", ""),
    })

    response = result.get("response")

    conversation_id = (
        payload.get("conversation_id")
        or payload.get("chat_id")
    )

    channel = f"{REDIS_CHANNEL_PREFIX}:{conversation_id}"

    redis_message = {
        "message_id": payload.get("message_id"),
        "agent_id": AGENT_ID,
        "response": response,
        "status": "COMPLETED",
    }

    redis_client.publish(
        channel,
        json.dumps(redis_message, ensure_ascii=False),
    )

    logger.info(
        "Resposta publicada no Redis: %s",
        channel,
    )


# =========================================================
# CALLBACK RABBITMQ
# =========================================================

def on_message(ch, method, properties, body):

    try:

        payload = json.loads(body)

        logger.info(
            "Mensagem recebida: %s",
            payload.get("message_id"),
        )

        process_message(payload)

        # Confirma que a mensagem foi processada
        ch.basic_ack(
            delivery_tag=method.delivery_tag
        )

    except Exception:

        logger.exception(
            "Erro ao processar mensagem"
        )

        # Devolve a mensagem para a fila
        ch.basic_nack(
            delivery_tag=method.delivery_tag,
            requeue=True,
        )


# =========================================================
# MAIN
# =========================================================

def main():

    logger.info(
        "Iniciando worker agent=%s queue=%s",
        AGENT_ID,
        RABBITMQ_QUEUE,
    )

    channel = rabbitmq_conn.channel

    channel.queue_declare(
        queue=RABBITMQ_QUEUE,
        durable=True,
    )

    # Processa uma mensagem por vez
    channel.basic_qos(
        prefetch_count=1,
    )

    channel.basic_consume(
        queue=RABBITMQ_QUEUE,
        on_message_callback=on_message,
        auto_ack=False,
    )

    logger.info(
        "Worker aguardando mensagens..."
    )

    try:
        # Fica rodando indefinidamente
        channel.start_consuming()

    except KeyboardInterrupt:
        logger.info(
            "Encerrando worker..."
        )

    finally:
        rabbitmq_conn.close()
        redis_conn.close()


if __name__ == "__main__":
    main()