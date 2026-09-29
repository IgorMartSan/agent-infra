import asyncio
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.langchain_agents import rsa_agent as agent

pytestmark = pytest.mark.usefixtures("rsa_env")


class FakeMCPClient:
    def __init__(self, config):
        self.config = config
        FakeMCPClient.last_config = config

    @asynccontextmanager
    async def session(self, server_name):
        yield object()


async def fake_load_mcp_tools(session):
    return []


class FakeAgent:
    def __init__(self, messages):
        self.messages = messages

    async def ainvoke(self, payload, config):
        return {"messages": self.messages}


def test_uses_mcp_result_when_model_response_is_empty(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_PATH", "/tmp/mcp.py")
    monkeypatch.setattr(agent, "MultiServerMCPClient", FakeMCPClient)
    monkeypatch.setattr(agent, "load_mcp_tools", fake_load_mcp_tools)
    monkeypatch.setattr(agent, "get_chat_model", lambda: object())
    messages = [
        ToolMessage(content="Tabela accounts (2 colunas):\n  id (integer), name (text)", tool_call_id="tool-1"),
        AIMessage(content=""),
    ]
    monkeypatch.setattr(agent, "create_agent", lambda **kwargs: FakeAgent(messages))

    result = asyncio.run(agent.chat_node({"messages": [HumanMessage(content="Liste as tabelas")], "thread_id": "test"}))

    assert result["response"] == "Tabela accounts (2 colunas):\n  id (integer), name (text)"
    assert "env" not in FakeMCPClient.last_config["rsa-db"]


def test_listing_tables_returns_tool_result_instead_of_generic_model_text(monkeypatch):
    monkeypatch.setattr(agent, "MultiServerMCPClient", FakeMCPClient)
    monkeypatch.setattr(agent, "load_mcp_tools", fake_load_mcp_tools)
    monkeypatch.setattr(agent, "get_chat_model", lambda: object())
    monkeypatch.setattr(
        agent,
        "create_agent",
        lambda **kwargs: FakeAgent(
            [
                ToolMessage(content="Tabela accounts (1 coluna): id", tool_call_id="tool-1"),
                AIMessage(content="As tabelas foram listadas."),
            ]
        ),
    )

    result = asyncio.run(agent.chat_node({"messages": [HumanMessage(content="Liste as tabelas")]}))

    assert result["response"] == "Tabela accounts (1 coluna): id"


def test_full_catalog_listing_uses_every_service_and_menu_path():
    catalog = {
        "services": [
            {"name": "Instalar câmera", "menu_path": ["Catálogo", "Infraestrutura", "Câmeras", "Instalar câmera"]},
            {"name": "Solicitar demandas", "menu_path": ["Catálogo", "Aplicações", "Nível 1", "Solicitar demandas"]},
            {"name": "Solicitar demandas", "menu_path": ["Catálogo", "Aplicações", "Nível 2", "Solicitar demandas"]},
        ]
    }
    response = agent._catalog_listing([{"type": "text", "text": json.dumps(catalog)}])

    assert [line for line in response.splitlines() if line[:1].isdigit()] == [
        "1. Instalar câmera",
        "2. Solicitar demandas",
        "3. Solicitar demandas",
    ]
    assert "Catálogo > Infraestrutura > Câmeras\n1. Instalar câmera" in response
    assert "Catálogo > Aplicações > Nível 1\n2. Solicitar demandas" in response
    assert "Catálogo > Aplicações > Nível 2\n3. Solicitar demandas" in response
    assert "id" not in response.casefold()


@pytest.mark.parametrize(
    "question",
    [
        "Mostre os serviços",
        "Quais serviços existem?",
        "Quais são todos os serviços disponíveis no catálogo?",
        "Quero ver o catálogo",
        "Serviços?",
        "Me fale os serviços",
        "Quais os serviços do RSA?",
        "Quais os serviços?",
    ],
)
def test_general_catalog_questions_take_direct_listing_path(question):
    assert agent._is_catalog_listing(question)


@pytest.mark.parametrize(
    "question",
    [
        "Qual serviço para instalar câmeras?",
        "Liste os serviços de câmeras",
        "Quais serviços do PIMS existem?",
        "Liste os serviços e seus formulários",
    ],
)
def test_specific_questions_stay_with_model(question):
    assert not agent._is_catalog_listing(question)


@pytest.mark.parametrize("question", ["Mostre os serviços", "Quais os serviços do RSA?", "Quais os serviços?"])
def test_chat_lists_catalog_without_model(monkeypatch, question):
    class CatalogTool:
        name = "list_services_with_done_examples"

        async def ainvoke(self, payload):
            assert payload == {}
            return [
                {
                    "type": "text",
                    "text": json.dumps(
                        {
                            "services": [
                                {"name": "Instalar câmera", "menu_path": ["Catálogo", "Câmeras", "Instalar câmera"]},
                                {"name": "Reparar câmera", "menu_path": ["Catálogo", "Câmeras", "Reparar câmera"]},
                            ]
                        }
                    ),
                }
            ]

    async def load_catalog_tool(session):
        return [CatalogTool()]

    monkeypatch.setattr(agent, "MultiServerMCPClient", FakeMCPClient)
    monkeypatch.setattr(agent, "load_mcp_tools", load_catalog_tool)
    monkeypatch.setattr(agent, "create_agent", lambda **kwargs: pytest.fail("Listagem não deve chamar o modelo"))

    result = asyncio.run(agent.chat_node({"messages": [HumanMessage(content=question)]}))

    assert "\n1. Instalar câmera\n2. Reparar câmera" in result["response"]
    assert "Instalar câmera" in result["response"]
    assert "Reparar câmera" in result["response"]


def test_raises_when_model_and_tool_have_no_response(monkeypatch):
    monkeypatch.setenv("MCP_SERVER_PATH", "/tmp/mcp.py")
    monkeypatch.setattr(agent, "MultiServerMCPClient", FakeMCPClient)
    monkeypatch.setattr(agent, "load_mcp_tools", fake_load_mcp_tools)
    monkeypatch.setattr(agent, "get_chat_model", lambda: object())
    monkeypatch.setattr(agent, "create_agent", lambda **kwargs: FakeAgent([AIMessage(content="")]))

    with pytest.raises(RuntimeError, match="resposta vazia"):
        asyncio.run(agent.chat_node({"messages": [HumanMessage(content="Oi")], "thread_id": "test"}))
