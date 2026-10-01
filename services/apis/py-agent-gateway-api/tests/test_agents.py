from unittest.mock import Mock

from fastapi.testclient import TestClient

from infra.redis.agent_repository import AgentRepository
from main import app


def test_lists_available_agents(resources):
    resources.agents.list_available.return_value = [{"agent_id": "argus-agent"}, {"agent_id": "simple-agent"}]
    with TestClient(app) as client:
        response = client.get("/api/v1/agents")
    assert response.status_code == 200
    assert response.json() == {"agents": resources.agents.list_available.return_value}


def test_repository_decodes_keys_and_deduplicates():
    redis = Mock()
    redis.scan_iter.return_value = [
        b"agent:online:simple-agent",
        "agent:online:argus-agent",
        b"agent:online:simple-agent",
    ]
    assert AgentRepository(redis).list_available() == [{"agent_id": "argus-agent"}, {"agent_id": "simple-agent"}]


def test_unavailable_agent_returns_503(resources):
    resources.agents.is_available.return_value = False
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/messages", json={"application_id": "app", "agent_id": "missing-agent", "message": "Olá"}
        )
    assert response.status_code == 503
    assert response.headers["retry-after"] == "30"
    resources.producer.publish.assert_not_called()


def test_registry_failure_returns_503(resources):
    resources.agents.list_available.side_effect = ConnectionError("Redis offline")
    with TestClient(app) as client:
        response = client.get("/api/v1/agents")
    assert response.status_code == 503
