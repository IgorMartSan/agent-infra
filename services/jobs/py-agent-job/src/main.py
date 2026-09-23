"""Worker didático: RabbitMQ → Agente (via AGENT_ID) → Redis Pub/Sub.

Variáveis de ambiente obrigatórias (definidas no .env ou compose):
- RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USER, RABBITMQ_PASSWORD
- RABBITMQ_QUEUE (fila que este worker consome)
- REDIS_HOST, REDIS_PORT
- AGENT_ID (ex: rsa-agent)

As demais configurações possuem padrões sensíveis no próprio código.
"""
import asyncio
import json
import logging
import os

import pika
import redis.asyncio as aioredis
from dotenv import load_dotenv

from agents.registry import get_agent_graph

load_dotenv()

# === Configurações com padrões no código ===
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
RABBITMQ_EXCHANGE = os.getenv("RABBITMQ_EXCHANGE", "agent.requests")
RABBITMQ_ROUTING_KEY = os.getenv("RABBITMQ_ROUTING_KEY", "")
RABBITMQ_PREFETCH = int(os.getenv("RABBITMQ_PREFETCH_COUNT", "1"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None) or None
REDIS_CHANNEL_PREFIX = os.getenv("REDIS_RESPONSE_CHANNEL_PREFIX", "chat:response")

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Variável obrigatória não definida: {name}")
    return value


async def publish_response(redis_client: aioredis.Redis, payload: dict, response: str) -> None:
    """Publica a resposta do agente no canal Pub/Sub do Redis."""
    conversation_id = payload.get("conversation_id") or payload.get("chat_id") or "unknown"
    channel = f"{REDIS_CHANNEL_PREFIX}:{conversation_id}"
    message = json.dumps({
        "message_id": payload.get("message_id"),
        "agent_id": payload.get("agent_id"),
        "response": response,
        "status": "COMPLETED",
    }, ensure_ascii=False)
    subscribers = await redis_client.publish(channel, message)
    logger.info("Resposta publicada: channel=%s subscribers=%s", channel, subscribers)


async def process_message(payload: dict, agent_graph, redis_client: aioredis.Redis) -> None:
    """Executa o agente e publica o resultado no Redis."""
    message = payload.get("message", "").strip()
    if not message:
        logger.warning("Mensagem vazia recebida; ignorando.")
        return

    try:
        result = await agent_graph.ainvoke({
            "message": message,
            "response": "",
            "thread_id": payload.get("thread_id", ""),
        })
        response = result.get("response", "").strip()
        if not response:
            raise RuntimeError("Agente retornou resposta vazia.")
        await publish_response(redis_client, payload, response)
    except Exception:
        logger.exception("Falha ao processar mensagem: message_id=%s", payload.get("message_id"))


def on_message(ch, method, properties, body, agent_graph, redis_client, loop):
    """Callback síncrono do Pika que delega ao handler async."""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        logger.error("Payload inválido (não é JSON); descartando.")
        ch.basic_ack(delivery_tag=method.delivery_tag)
        return

    logger.info("Mensagem recebida: message_id=%s agent_id=%s", payload.get("message_id"), payload.get("agent_id"))

    future = asyncio.run_coroutine_threadsafe(
        process_message(payload, agent_graph, redis_client), loop
    )
    try:
        future.result(timeout=300)
    except Exception:
        logger.exception("Erro no processamento async")
    finally:
        ch.basic_ack(delivery_tag=method.delivery_tag)


def main() -> None:
    agent_id = _require_env("AGENT_ID")
    rabbitmq_host = _require_env("RABBITMQ_HOST")
    rabbitmq_port = int(_require_env("RABBITMQ_PORT"))
    rabbitmq_user = _require_env("RABBITMQ_USER")
    rabbitmq_password = _require_env("RABBITMQ_PASSWORD")
    queue = _require_env("RABBITMQ_QUEUE")
    redis_host = _require_env("REDIS_HOST")
    redis_port = int(_require_env("REDIS_PORT"))

    logger.info("Iniciando worker: agent_id=%s queue=%s", agent_id, queue)

    # Carrega o grafo do agente definido por AGENT_ID
    agent_graph = get_agent_graph(agent_id)
    logger.info("Agente carregado: %s", agent_id)

    # Conexão Redis async
    loop = asyncio.new_event_loop()
    redis_client = loop.run_until_complete(
        aioredis.from_url(
            f"redis://{redis_host}:{redis_port}",
            db=REDIS_DB,
            password=REDIS_PASSWORD,
            decode_responses=True,
        )
    )

    # Conexão RabbitMQ (síncrona via Pika)
    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_password)
    parameters = pika.ConnectionParameters(
        host=rabbitmq_host,
        port=rabbitmq_port,
        credentials=credentials,
        heartbeat=600,
    )
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()
    channel.queue_declare(queue=queue, durable=True)
    channel.basic_qos(prefetch_count=RABBITMQ_PREFETCH)

    def callback(ch, method, properties, body):
        on_message(ch, method, properties, body, agent_graph, redis_client, loop)

    channel.basic_consume(queue=queue, on_message_callback=callback)
    logger.info("Aguardando mensagens na fila '%s'...", queue)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        logger.info("Worker encerrado pelo usuário.")
    finally:
        channel.stop_consuming()
        connection.close()
        loop.run_until_complete(redis_client.aclose())
        loop.close()


if __name__ == "__main__":
    main()