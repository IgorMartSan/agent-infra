import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.tools import StructuredTool

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.langchain_agents import rsa_agent as agent

pytestmark = pytest.mark.usefixtures("rsa_env")


class FakeMCPClient:
    def __init__(self, config):
        pass

    @asynccontextmanager
    async def session(self, server_name):
        yield object()


class ToolCallingModel(FakeMessagesListChatModel):
    def bind_tools(self, tools, **kwargs):
        return self


def test_camera_request_executes_discovered_tool_with_dynamic_prompt(monkeypatch):
    calls = []

    async def find_service():
        calls.append("catalog")
        return '{"services": [{"name": "Instalar câmera", "menu_path": ["Catálogo", "Câmeras", "Instalar câmera"], "form": [{"label": "Local de instalação", "required": true}]}]}'

    tool = StructuredTool.from_function(
        coroutine=find_service,
        name="discover_camera_services",
        description="Consulta serviços, caminhos no menu e formulários para instalar câmeras. Somente leitura.",
    )

    async def load_tools(session):
        return [tool]

    model = ToolCallingModel(
        responses=[
            AIMessage(content="", tool_calls=[{"name": tool.name, "args": {}, "id": "camera-call"}]),
            AIMessage(content="Use Instalar câmera em Catálogo → Câmeras. No formulário, informe Local de instalação."),
        ]
    )
    prompts = []
    real_create_agent = agent.create_agent

    def create_agent(**kwargs):
        prompts.append(kwargs["system_prompt"])
        return real_create_agent(**kwargs)

    monkeypatch.setattr(agent, "MultiServerMCPClient", FakeMCPClient)
    monkeypatch.setattr(agent, "load_mcp_tools", load_tools)
    monkeypatch.setattr(agent, "get_chat_model", lambda: model)
    monkeypatch.setattr(agent, "create_agent", create_agent)

    result = asyncio.run(agent.chat_node({"messages": [HumanMessage(content="quero instala uma camera")]}))

    assert calls == ["catalog"]
    assert tool.name in prompts[0]
    assert tool.description in prompts[0]
    assert '"parameters"' in prompts[0]
    assert "Local de instalação" in result["response"]


def test_inventory_uses_all_current_tools_and_drops_unavailable_capabilities():
    first = StructuredTool.from_function(lambda: "ok", name="catalog", description="Consultar catálogo")
    second = StructuredTool.from_function(lambda: "ok", name="status", description="Consultar andamento")

    prompt = agent._mcp_tools_prompt([first, second])
    assert first.description in prompt
    assert second.description in prompt
    assert second.description not in agent._mcp_tools_prompt([first])
    assert agent._mcp_tools_prompt([]).endswith("[]")
