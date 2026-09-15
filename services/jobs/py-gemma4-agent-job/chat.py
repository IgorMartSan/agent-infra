import json
import os
import threading
import time

import httpx
import redis
from dotenv import load_dotenv

load_dotenv()

API_URL = os.environ["CHAT_API_URL"]
REDIS_HOST = os.environ["REDIS_HOST"]
REDIS_PORT = int(os.environ["REDIS_PORT"])
CHANNEL_PREFIX = os.environ["REDIS_RESPONSE_CHANNEL_PREFIX"]

APPLICATION_ID = os.environ["CHAT_APPLICATION_ID"]
CHAT_ID = os.environ["CHAT_CHAT_ID"]
AGENT_ID = os.environ["CHAT_AGENT_ID"]

received_events = []


def subscribe_to_responses(client: redis.Redis, application_id: str, chat_id: str) -> redis.client.PubSub:
    pubsub = client.pubsub()
    pubsub.subscribe(f"{CHANNEL_PREFIX}:{application_id}:{chat_id}")
    return pubsub


def wait_for_response(pubsub: redis.client.PubSub, timeout: float = 60.0) -> dict | None:
    listener = threading.Thread(target=listen_for_events, args=(pubsub,), daemon=True)
    listener.start()

    deadline = time.time() + timeout
    while time.time() < deadline:
        for event in received_events:
            if event.get("type") == "message.completed":
                return event
        time.sleep(0.1)

    return None


def listen_for_events(pubsub: redis.client.PubSub) -> None:
    for message in pubsub.listen():
        if message["type"] != "message":
            continue

        try:
            event = json.loads(message["data"])
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue

        received_events.append(event)


def send_message(message: str) -> str:
    payload = {
        "application_id": APPLICATION_ID,
        "user_id": "chat-cli-user",
        "chat_id": CHAT_ID,
        "agent_id": AGENT_ID,
        "message": message,
    }

    response = httpx.post(API_URL, json=payload, timeout=10)
    response.raise_for_status()

    return response.json()["message_id"]


def main() -> None:
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        socket_connect_timeout=3,
        socket_timeout=3,
    )

    redis_client.ping()

    print("Chat CLI - envie mensagens para o agente (Ctrl+C para sair)")
    print(f"API: {API_URL}")
    print(f"Canal: {CHANNEL_PREFIX}:{APPLICATION_ID}:{CHAT_ID}")
    print()

    pubsub = subscribe_to_responses(redis_client, APPLICATION_ID, CHAT_ID)

    try:
        while True:
            message = input("voce > ").strip()
            if not message:
                continue

            received_events.clear()

            started_at = time.perf_counter()
            send_message(message)
            print("aguardando resposta...", flush=True)

            event = wait_for_response(pubsub)
            elapsed_seconds = time.perf_counter() - started_at
            if event is None:
                print("agente > (sem resposta dentro do timeout)")
                print(f"tempo decorrido: {elapsed_seconds:.2f}s")
            else:
                print(f"agente > {event.get('content')}")
                print(f"tempo de resposta: {elapsed_seconds:.2f}s")
            print()
    except (KeyboardInterrupt, EOFError):
        print()
        print("Encerrando o chat.")
    finally:
        pubsub.close()
        redis_client.close()


if __name__ == "__main__":
    main()
