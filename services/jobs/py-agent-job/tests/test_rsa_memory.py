import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.catalog import Agent, _thread_id_for
from agents.langchain_agents import rsa_agent as agent
from entity.message import AgentMessage

pytestmark = pytest.mark.usefixtures("rsa_env")


class FakeMCPClient:
    def __init__(self, config):
        self.config = config

    @asynccontextmanager
    async def session(self, server_name):
        yield object()


async def fake_load_mcp_tools(session):
    return []


def test_rsa_summarizes_old_messages_and_keeps_last_exchange(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_PATH", "/tmp/mcp.py")
    monkeypatch.setenv("RSA_MEMORY_MAX_MESSAGES", "4")
    monkeypatch.setattr(agent, "MultiServerMCPClient", FakeMCPClient)
    monkeypatch.setattr(agent, "load_mcp_tools", fake_load_mcp_tools)
    seen_histories = []
    seen_prompts = []
    summary_inputs = []

    class FakeSummaryModel:
        async def ainvoke(self, messages):
            summary_inputs.append([message.content for message in messages])
            return AIMessage(content="Resumo das perguntas anteriores")

    class FakeAgent:
        async def ainvoke(self, payload, config):
            seen_histories.append([message.content for message in payload["messages"]])
            return {"messages": [AIMessage(content=f"resposta {len(seen_histories)}")]}

    def fake_create_agent(**kwargs):
        seen_prompts.append(kwargs["system_prompt"])
        return FakeAgent()

    monkeypatch.setattr(agent, "get_chat_model", lambda: FakeSummaryModel())
    monkeypatch.setattr(agent, "create_agent", fake_create_agent)
    graph = agent.build_graph(agent.InMemorySaver())
    chat_id = uuid4().hex

    with asyncio.Runner() as runner:
        rsa_agent = Agent("rsa-agent", graph, runner)
        for index in range(1, 5):
            assert (
                rsa_agent.invoke(AgentMessage("app", f"msg-{index}", "rsa-agent", f"pergunta {index}", chat_id, "user"))
                == f"resposta {index}"
            )

        other_response = rsa_agent.invoke(
            AgentMessage("app", "msg-outro", "rsa-agent", "outra conversa", uuid4().hex, "user")
        )

    assert seen_histories[0] == ["pergunta 1"]
    assert seen_histories[1] == ["pergunta 1", "resposta 1", "pergunta 2"]
    assert seen_histories[2] == ["pergunta 1", "resposta 1", "pergunta 2", "resposta 2", "pergunta 3"]
    assert seen_histories[3] == ["pergunta 3", "resposta 3", "pergunta 4"]
    assert seen_histories[4] == ["outra conversa"]
    assert other_response == "resposta 5"
    assert "Resumo das perguntas anteriores" in seen_prompts[3]
    assert "Resumo das perguntas anteriores" not in seen_prompts[4]
    assert summary_inputs[0][1:5] == ["pergunta 1", "resposta 1", "pergunta 2", "resposta 2"]

    thread_id = _thread_id_for(
        {"application_id": "app", "user_id": "user", "chat_id": chat_id, "agent_id": "rsa-agent"}
    )
    state = graph.get_state({"configurable": {"thread_id": thread_id}})
    assert state.values["summary"] == "Resumo das perguntas anteriores"
    assert [message.content for message in state.values["messages"]] == [
        "pergunta 3",
        "resposta 3",
        "pergunta 4",
        "resposta 4",
    ]
