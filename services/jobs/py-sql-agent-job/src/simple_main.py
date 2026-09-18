"""Fluxo simples e didático: RabbitMQ -> agente -> Redis Pub/Sub.

Versão mínima do main.py, sem loop de reconexão nem repositórios,
para deixar visível o fluxo de dados em 3 passos:

1. Pega a mensagem do RabbitMQ (consume).
2. Joga a mensagem para o agente SQL (graph.invoke).
3. Pega a resposta e envia para o Redis Pub/Sub (publish).
"""

import json
import os

import pika
import redis
from dotenv import load_dotenv

from graph.graph import graph

load_dotenv()


def run() -> None:
    # --- Conexões ---
    rabbit = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=os.environ["RABBITMQ_HOST"],
            port=int(os.environ["RABBITMQ_PORT"]),
            credentials=pika.PlainCredentials(
                os.environ["RABBITMQ_USER"],
                os.environ["RABBITMQ_PASSWORD"],
            ),
        )
    )
    redis_client = redis.Redis(
        host=os.environ["REDIS_HOST"],
        port=int(os.environ["REDIS_PORT"]),
    )
    channel = rabbit.channel()
    channel.queue_declare(queue=os.environ["RABBITMQ_QUEUE"], durable=True)

    # --- 1. Pega a mensagem do RabbitMQ ---
    method, _, body = channel.basic_get(queue=os.environ["RABBITMQ_QUEUE"], auto_ack=False)
    if body is None:
        print("Nenhuma mensagem na fila.")
        rabbit.close()
        redis_client.close()
        return

    payload = json.loads(body)
    print(f"1. Recebido do RabbitMQ: {payload.get('message')}")

    # --- 2. Joga a mensagem para o agente ---
    result = graph.invoke({"message": payload["message"], "response": ""})
    response = result["response"]
    print(f"2. Resposta do agente: {response}")

    # --- 3. Envia a resposta para o Redis Pub/Sub ---
    event = {
        "type": "message.completed",
        "application_id": payload.get("application_id"),
        "conversation_id": payload.get("chat_id"),
        "message_id": payload.get("message_id"),
        "agent_id": payload.get("agent_id"),
        "content": response,
    }
    canal = (
        f"{os.environ['REDIS_RESPONSE_CHANNEL_PREFIX']}:"
        f"{payload.get('application_id')}:{payload.get('chat_id')}"
    )
    subscribers = redis_client.publish(canal, json.dumps(event, ensure_ascii=False))
    print(f"3. Publicado no canal {canal} ({subscribers} inscrito(s)).")

    # Confirma o processamento só depois de publicar.
    channel.basic_ack(delivery_tag=method.delivery_tag)
    rabbit.close()
    redis_client.close()


if __name__ == "__main__":
    run()