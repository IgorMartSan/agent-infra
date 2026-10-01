from fastapi.testclient import TestClient

from main import app
from service.conversation_lock import ConversationLockUnavailable
from service.queue_threshold import QueueOverloaded


def valid_payload():
    return {
        "application_id": "erp",
        "user_id": "user-123",
        "chat_id": "chat-456",
        "agent_id": "simple-agent",
        "message": "Olá",
        "metadata": {"source": "test"},
        "delivery": {"type": "NONE", "target": None, "channel": None, "space_id": None},
    }


def test_health_endpoint():
    with TestClient(app) as client:
        response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Agent API is running"}


def test_message_is_published_before_accepted(resources):
    with TestClient(app) as client:
        response = client.post("/api/v1/messages", json=valid_payload())
    assert response.status_code == 202
    published = resources.producer.publish.call_args.kwargs
    assert published["message"] == {"message_id": response.json()["message_id"], **valid_payload()}
    assert published["routing_key"] == "agent.simple"
    resources.lock.acquire.assert_called_once_with(application_id="erp", chat_id="chat-456", agent_id="simple-agent")
    resources.lock.release.assert_not_called()


def test_busy_conversation_returns_409(resources):
    resources.lock.acquire.side_effect = ConversationLockUnavailable("Aguarde a resposta anterior.")
    with TestClient(app) as client:
        response = client.post("/api/v1/messages", json=valid_payload())
    assert response.status_code == 409
    resources.producer.publish.assert_not_called()


def test_invalid_payload_is_rejected():
    payload = valid_payload()
    payload.pop("agent_id")
    with TestClient(app) as client:
        response = client.post("/api/v1/messages", json=payload)
    assert response.status_code == 422


def test_publish_failure_returns_503_and_releases_lock(resources):
    resources.producer.publish.side_effect = ConnectionError("offline")
    with TestClient(app) as client:
        response = client.post("/api/v1/messages", json=valid_payload())
    assert response.status_code == 503
    resources.lock.release.assert_called_once_with(application_id="erp", chat_id="chat-456", agent_id="simple-agent")


def test_overloaded_queue_returns_retry_after_without_locking(resources):
    resources.queue.check.side_effect = QueueOverloaded("Fila cheia.")
    with TestClient(app) as client:
        response = client.post("/api/v1/messages", json=valid_payload())
    assert response.status_code == 503
    assert response.headers["retry-after"] == "30"
    resources.lock.acquire.assert_not_called()
    resources.producer.publish.assert_not_called()


def test_queue_connection_failure_returns_503_before_locking(resources):
    resources.queue.check.side_effect = ConnectionError("conexão encerrada")
    with TestClient(app) as client:
        response = client.post("/api/v1/messages", json=valid_payload())
    assert response.status_code == 503
    resources.lock.acquire.assert_not_called()
    resources.producer.publish.assert_not_called()
