import asyncio
import sys
from importlib import import_module
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.langchain_agents import agent_runtime
from agents.langchain_agents.agent_runtime import AGENTS, AgentRuntime, get_agent
from entity.message import AgentMessage


def test_registered_agents_load_with_common_runtime():
    for module_path in AGENTS.values():
        import_module(module_path)

    with get_agent("simple-agent") as agent:
        response = agent.invoke(AgentMessage("app", "message", "simple-agent", "olá", "chat", "user"))

    assert "Eu recebi a mensagem: olá" in response


def test_runtime_passes_langfuse_config_to_graph(monkeypatch):
    handler = object()
    monkeypatch.setattr(agent_runtime, "CallbackHandler", lambda: handler)
    expected_config = {
        "callbacks": [handler],
        "configurable": {"thread_id": "conversation-1"},
        "metadata": {"langfuse_session_id": "conversation-1", "langfuse_tags": ["argus-agent"]},
    }

    class Graph:
        async def ainvoke(self, state, config):
            assert config == expected_config
            assert state["thread_id"] == "conversation-1"
            return {"response": "ok"}

    with asyncio.Runner() as runner:
        runtime = AgentRuntime("argus-agent", object(), runner)
        runtime.graph = Graph()
        response = runtime.invoke(AgentMessage("app", "msg", "argus-agent", "pergunta", "conversation-1"))

    assert response == "ok"


@pytest.mark.parametrize("agent_id", ["simple-agent", "rsa-agent"])
def test_wrapped_graphs_receive_langfuse_config(agent_id, monkeypatch):
    handler = object()
    monkeypatch.setattr(agent_runtime, "CallbackHandler", lambda: handler)
    expected_config = {
        "callbacks": [handler],
        "configurable": {"thread_id": "conversation-1"},
        "metadata": {"langfuse_session_id": "conversation-1", "langfuse_tags": [agent_id]},
    }

    class Graph:
        async def ainvoke(self, state, config):
            assert config == expected_config
            return {"response": "ok"}

    with asyncio.Runner() as runner:
        runtime = AgentRuntime(agent_id, import_module(AGENTS[agent_id]), runner)
        runtime.graph = Graph()
        response = runtime.invoke(AgentMessage("app", "msg", agent_id, "pergunta", "conversation-1"))

    assert response == "ok"
