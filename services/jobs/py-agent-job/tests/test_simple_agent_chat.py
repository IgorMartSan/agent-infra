import asyncio
import json
import sys
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import Mock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import main as worker
from agents.catalog import Agent as LoadedAgent
from agents.catalog import AgentProcessingError, get_agent
from agents.langchain_agents.simple_agent.graph import graph
from entity.message import AgentMessage, InvalidMessageError
from infra.redis.response_repository import AgentResponsePubSubRepository


def sample_message(message_id="msg-1"):
    return AgentMessage("app", message_id, "simple-agent", "Olá", chat_id="chat")


def test_simple_agent_repeats_message():
    result = graph.invoke({"message": "Olá, chat!", "response": ""})
    assert result["response"].endswith("Eu recebi a mensagem: Olá, chat!")


def test_get_agent_loads_and_invokes_graph():
    with get_agent("simple-agent") as agent:
        response = agent.invoke(sample_message())
    assert response.endswith("Eu recebi a mensagem: Olá")


def test_response_uses_chat_channel_and_ids():
    redis = Mock()
    redis.publish.return_value = 1
    connection = Mock()
    connection.get_client.return_value = redis
    publisher = AgentResponsePubSubRepository(connection)

    assert publisher.publish(AgentMessage("meu-app", "msg-1", "simple-agent", "Olá", chat_id="chat 1"), "Olá") == 1
    channel, payload = redis.publish.call_args.args
    assert channel == "chat:response:meu-app:chat%201"
    assert json.loads(payload) == {
        "type": "message.completed",
        "application_id": "meu-app",
        "conversation_id": "chat 1",
        "message_id": "msg-1",
        "agent_id": "simple-agent",
        "content": "Olá",
    }


def test_agent_reuses_async_loop():
    loops = []

    class Agent:
        async def ainvoke(self, state, config):
            loops.append(asyncio.get_running_loop())
            return {"response": state["message"]}

    with asyncio.Runner() as runner:
        agent = LoadedAgent("simple-agent", Agent(), runner)
        assert agent.invoke(sample_message("msg-1")) == "Olá"
        assert agent.invoke(sample_message("msg-2")) == "Olá"
    assert loops[0] is loops[1]


def test_agent_error_has_public_message():
    class Agent:
        async def ainvoke(self, state, config):
            raise RuntimeError("erro interno")

    with asyncio.Runner() as runner, pytest.raises(AgentProcessingError, match="Não foi possível processar"):
        LoadedAgent("simple-agent", Agent(), runner).invoke(sample_message())


def test_worker_publishes_agent_error_before_ack(monkeypatch):
    message = sample_message()
    error = AgentProcessingError("Falha ao processar.")
    agent = Mock()
    agent.invoke.side_effect = error
    publisher, conversation_lock, heartbeat, redis, rabbitmq = (Mock() for _ in range(5))
    publisher.publish.return_value = 1

    @contextmanager
    def fake_get_agent(agent_id):
        assert agent_id == "simple-agent"
        yield agent

    def messages():
        yield message
        raise KeyboardInterrupt

    rabbitmq.consume.return_value = messages()
    monkeypatch.setenv("AGENT_ID", "simple-agent")
    monkeypatch.setattr(worker, "load_dotenv", lambda: None)
    monkeypatch.setattr(worker, "setup_logger", lambda level: None)
    monkeypatch.setattr(worker, "get_agent", fake_get_agent)
    monkeypatch.setattr(worker, "RedisConnection", lambda: redis)
    monkeypatch.setattr(worker, "AgentRegistry", lambda client, agent_id: heartbeat)
    monkeypatch.setattr(worker, "AgentResponsePubSubRepository", lambda connection: publisher)
    monkeypatch.setattr(worker, "ConversationLock", lambda client: conversation_lock)
    monkeypatch.setattr(worker, "RabbitMQConnection", lambda: rabbitmq)

    worker.main()

    publisher.publish.assert_called_once_with(message, str(error), failed=True)
    conversation_lock.release.assert_called_once_with("app", "chat", "simple-agent")
    rabbitmq.ack.assert_called_once()
    heartbeat.start.assert_called_once()
    heartbeat.stop.assert_called_once()


@pytest.mark.parametrize("payload", [None, [], {}, {"message": ""}, {"message": 123}])
def test_invalid_message_is_rejected(payload):
    with pytest.raises(InvalidMessageError):
        AgentMessage.from_payload(payload)
