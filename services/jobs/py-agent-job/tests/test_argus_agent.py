import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.catalog import _thread_id_for
from agents.langchain_agents.argus_agent.graph import nodes
from agents.langchain_agents.argus_agent.graph.graph import graph


def test_argus_graph_invokes_sql_agent(monkeypatch):
    class FakeAgent:
        def __init__(self):
            self.input = None

        def get_state(self, config):
            return SimpleNamespace(values={"messages": []})

        def invoke(self, payload, config):
            self.input = payload
            return {"messages": [SimpleNamespace(content="  Resposta do banco  ")]}

    fake_agent = FakeAgent()
    monkeypatch.setattr(nodes, "build_sql_agent", lambda: fake_agent)

    result = asyncio.run(
        graph.ainvoke({"message": "Quais tabelas existem?", "response": "", "thread_id": "argus-test"})
    )

    assert result["response"] == "Resposta do banco"
    assert fake_agent.input["messages"][0]["content"] == "Quais tabelas existem?"


def test_argus_thread_is_stable_and_isolated():
    payload = {"application_id": "app", "user_id": "user-1", "chat_id": "chat-1", "agent_id": "argus-agent"}

    assert _thread_id_for(payload) == _thread_id_for(payload)
    assert _thread_id_for(payload) != _thread_id_for({**payload, "user_id": "user-2"})
    assert _thread_id_for(payload) != _thread_id_for({**payload, "chat_id": "chat-2"})
