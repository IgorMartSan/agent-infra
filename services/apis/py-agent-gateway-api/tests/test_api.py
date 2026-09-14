from fastapi.testclient import TestClient

import routers.message as message_router
from main import app


class FakeMessageService:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.messages: list[dict] = []

    def send(self, message: dict) -> None:
        if self.error:
            raise self.error
        self.messages.append(message)


def valid_payload() -> dict:
    return {
        'application_id': 'erp',
        'user_id': 'user-123',
        'chat_id': 'chat-456',
        'agent_id': 'agent-suporte',
        'message': 'Verifique o status do chamado 900.',
        'metadata': {'source': 'message-simulator'},
        'delivery': {
            'type': 'WEBSOCKET',
            'channel': 'erp:chat:456',
        },
    }


def test_health_endpoint() -> None:
    with TestClient(app) as client:
        response = client.get('/')

    assert response.status_code == 200
    assert response.json() == {'message': 'Agent API is running'}


def test_message_is_published_before_accepted(monkeypatch) -> None:
    service = FakeMessageService()
    monkeypatch.setattr(message_router, 'message_service', service)

    with TestClient(app) as client:
        response = client.post('/api/v1/messages', json=valid_payload())

    assert response.status_code == 202
    assert response.json()['status'] == 'ACCEPTED'
    assert response.json()['message_id'] == service.messages[0]['message_id']
    assert service.messages[0]['application_id'] == 'erp'
    assert service.messages[0]['metadata'] == {'source': 'message-simulator'}
    assert service.messages[0]['delivery']['type'] == 'WEBSOCKET'


def test_invalid_payload_is_rejected() -> None:
    payload = valid_payload()
    payload.pop('agent_id')

    with TestClient(app) as client:
        response = client.post('/api/v1/messages', json=payload)

    assert response.status_code == 422


def test_rabbitmq_failure_returns_503(monkeypatch) -> None:
    monkeypatch.setattr(
        message_router,
        'message_service',
        FakeMessageService(ConnectionError('RabbitMQ offline')),
    )

    with TestClient(app) as client:
        response = client.post('/api/v1/messages', json=valid_payload())

    assert response.status_code == 503
    assert response.json() == {
        'detail': 'RabbitMQ indisponível para receber a mensagem.',
    }
