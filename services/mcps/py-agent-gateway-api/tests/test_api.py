from fastapi.testclient import TestClient

import routers.agents as agents_router
import routers.message as message_router
from main import app
from service.conversation_lock import ConversationLockUnavailable
from service.queue_threshold import QueueOverloaded


class FakeRedisClient:
    """Redis fake: agente sempre disponível (chave de heartbeat presente)."""

    def exists(self, key: str) -> int:
        return 1

    def scan_iter(self, match: str, count: int) -> list[str]:
        return []


class FakeMessageService:
    def __init__(self, error: Exception | None = None):
        self.error = error
        self.messages: list[dict] = []

    def send(self, message: dict) -> None:
        if self.error:
            raise self.error
        self.messages.append(message)


class FakeConversationLock:
    def __init__(self, locked: bool = False):
        self.locked = locked
        self.acquired: list[tuple[str, str | None, str]] = []
        self.released: list[tuple[str, str | None, str]] = []

    def acquire(self, application_id: str, chat_id: str | None, agent_id: str) -> None:
        self.acquired.append((application_id, chat_id, agent_id))
        if self.locked:
            raise ConversationLockUnavailable(
                'Já existe uma mensagem em processamento para esta conversa. '
                'Aguarde a resposta anterior antes de enviar uma nova mensagem.'
            )

    def release(self, application_id: str, chat_id: str | None, agent_id: str) -> None:
        self.released.append((application_id, chat_id, agent_id))


class FakeQueueThreshold:
    def __init__(self, overloaded: bool = False):
        self.overloaded = overloaded
        self.checked: list[str] = []

    def check(self, queue_name: str) -> None:
        self.checked.append(queue_name)
        if self.overloaded:
            raise QueueOverloaded(
                'A fila de processamento está cheia no momento. '
                'Tente novamente em alguns instantes.'
            )


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
    lock = FakeConversationLock()
    monkeypatch.setattr(message_router, 'message_service', service)
    monkeypatch.setattr(message_router, 'conversation_lock', lock)
    monkeypatch.setattr(message_router, 'queue_threshold', FakeQueueThreshold())
    monkeypatch.setattr(agents_router, 'redis_client', FakeRedisClient())

    with TestClient(app) as client:
        response = client.post('/api/v1/messages', json=valid_payload())

    assert response.status_code == 202
    assert response.json()['status'] == 'ACCEPTED'
    assert response.json()['message_id'] == service.messages[0]['message_id']
    assert service.messages[0]['application_id'] == 'erp'
    assert service.messages[0]['metadata'] == {'source': 'message-simulator'}
    assert service.messages[0]['delivery']['type'] == 'WEBSOCKET'
    # O lock é adquirido na entrada com a chave da conversa.
    assert lock.acquired == [('erp', 'chat-456', 'agent-suporte')]
    # Publicado com sucesso: o lock não é liberado aqui (o worker libera).
    assert lock.released == []


def test_second_message_for_same_conversation_returns_409(monkeypatch) -> None:
    service = FakeMessageService()
    monkeypatch.setattr(message_router, 'message_service', service)
    monkeypatch.setattr(
        message_router,
        'conversation_lock',
        FakeConversationLock(locked=True),
    )
    monkeypatch.setattr(message_router, 'queue_threshold', FakeQueueThreshold())
    monkeypatch.setattr(agents_router, 'redis_client', FakeRedisClient())

    with TestClient(app) as client:
        response = client.post('/api/v1/messages', json=valid_payload())

    assert response.status_code == 409
    assert 'Aguarde a resposta anterior' in response.json()['detail']
    # A mensagem não é publicada no RabbitMQ.
    assert service.messages == []


def test_invalid_payload_is_rejected() -> None:
    payload = valid_payload()
    payload.pop('agent_id')

    with TestClient(app) as client:
        response = client.post('/api/v1/messages', json=payload)

    assert response.status_code == 422


def test_rabbitmq_failure_returns_503_and_releases_lock(monkeypatch) -> None:
    service = FakeMessageService(ConnectionError('RabbitMQ offline'))
    lock = FakeConversationLock()
    monkeypatch.setattr(message_router, 'message_service', service)
    monkeypatch.setattr(message_router, 'conversation_lock', lock)
    monkeypatch.setattr(message_router, 'queue_threshold', FakeQueueThreshold())
    monkeypatch.setattr(agents_router, 'redis_client', FakeRedisClient())

    with TestClient(app) as client:
        response = client.post('/api/v1/messages', json=valid_payload())

    assert response.status_code == 503
    assert response.json() == {
        'detail': 'RabbitMQ indisponível para receber a mensagem.',
    }
    # Publicação falhou: o lock é liberado para não travar a conversa.
    assert lock.released == [('erp', 'chat-456', 'agent-suporte')]


def test_overloaded_queue_returns_503_with_retry_after(monkeypatch) -> None:
    service = FakeMessageService()
    lock = FakeConversationLock()
    monkeypatch.setattr(message_router, 'message_service', service)
    monkeypatch.setattr(message_router, 'conversation_lock', lock)
    monkeypatch.setattr(
        message_router,
        'queue_threshold',
        FakeQueueThreshold(overloaded=True),
    )
    monkeypatch.setattr(agents_router, 'redis_client', FakeRedisClient())

    with TestClient(app) as client:
        response = client.post('/api/v1/messages', json=valid_payload())

    assert response.status_code == 503
    assert 'fila de processamento está cheia' in response.json()['detail']
    # O cliente é instruído a tentar novamente depois de alguns segundos.
    assert response.headers['retry-after'] == '30'
    # Nada é publicado e a conversa não é travada.
    assert service.messages == []
    assert lock.acquired == []