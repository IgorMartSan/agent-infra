from fastapi.testclient import TestClient

import routers.agents as agents_router
from main import app


class FakeRedisClient:
    def __init__(self, keys: list[str] | None = None, available: bool = True) -> None:
        self.keys = keys or []
        self.available = available
        self.checked: list[str] = []

    def exists(self, key: str) -> int:
        self.checked.append(key)
        return 1 if self.available else 0

    def scan_iter(self, match: str, count: int) -> list[str]:
        return [key.removeprefix(match.replace('*', '')) for key in self.keys]


def test_lists_available_agents(monkeypatch) -> None:
    monkeypatch.setattr(
        agents_router,
        'redis_client',
        FakeRedisClient(keys=['agent:online:sql-agent', 'agent:online:suporte-agent']),
    )

    with TestClient(app) as client:
        response = client.get('/api/v1/agents')

    assert response.status_code == 200
    assert response.json() == {
        'agents': [
            {'agent_id': 'sql-agent'},
            {'agent_id': 'suporte-agent'},
        ],
    }


def test_message_to_unavailable_agent_returns_503(monkeypatch) -> None:
    monkeypatch.setattr(
        agents_router,
        'redis_client',
        FakeRedisClient(available=False),
    )

    from schemas.message import MessageRequest  # noqa: F401

    payload = {
        'application_id': 'erp',
        'user_id': 'user-123',
        'chat_id': 'chat-456',
        'agent_id': 'agent-suporte',
        'message': 'Verifique o status do chamado 900.',
    }

    with TestClient(app) as client:
        response = client.post('/api/v1/messages', json=payload)

    assert response.status_code == 503
    assert 'Não há workers ativos' in response.json()['detail']
    assert response.headers['retry-after'] == '30'