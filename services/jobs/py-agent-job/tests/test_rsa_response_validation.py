import asyncio
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.langchain_agents.rsa_flow import graph as flow
from agents.langchain_agents.rsa_flow import nodes, validation

pytestmark = pytest.mark.usefixtures("rsa_env")


def verdict(status="complete", requires_tool=True, feedback=""):
    return validation.ResponseValidation(status=status, requires_tool=requires_tool, feedback=feedback)


class FakeValidator:
    def __init__(self, verdicts):
        self.verdicts = iter(verdicts)
        self.evidence = []

    def with_structured_output(self, schema, method):
        assert schema is validation.ResponseValidation
        assert method == "function_calling"
        return self

    async def ainvoke(self, messages):
        self.evidence.append(json.loads(messages[-1].content))
        result = next(self.verdicts)
        if isinstance(result, Exception):
            raise result
        return result


def install_agent(monkeypatch, replies, verdicts, tools=None):
    calls = []
    replies = iter(replies)
    validator = FakeValidator(verdicts)

    class CatalogInfo:
        name = "catalog"
        description = "Consulta serviços"

        def __init__(self):
            self.args = {}

    tools = tools if tools is not None else [CatalogInfo()]

    class Client:
        def __init__(self, config):
            pass

        @asynccontextmanager
        async def session(self, name):
            yield object()

    async def load_tools(session):
        return tools

    async def fake_planner(state):
        question = next(message.content for message in reversed(state["messages"]) if isinstance(message, HumanMessage))
        # Estes testes isolam a validação; o planner real tem sua própria suíte.
        decision = "respond" if question == "Olá" else "tools"
        return {
            "plan": {
                "decision": decision,
                "normalized_question": question,
                "selected_tools": [tool.name for tool in tools] if decision == "tools" else [],
                "steps": ["Atenda ao pedido"],
            },
            "tools_inventory": nodes._mcp_tools_prompt(tools),
        }

    class ResponseModel:
        async def ainvoke(self, messages):
            calls.append((messages[1:], messages[0].content))
            return next(replies)[-1]

    def create_agent(**kwargs):
        class Agent:
            async def ainvoke(self, payload, config):
                calls.append((payload["messages"], kwargs["system_prompt"]))
                return {"messages": [*payload["messages"], *next(replies)]}

        return Agent()

    monkeypatch.setattr(nodes, "MultiServerMCPClient", Client)
    monkeypatch.setattr(nodes, "load_mcp_tools", load_tools)
    monkeypatch.setattr(nodes, "get_chat_model", ResponseModel)
    monkeypatch.setattr(nodes, "create_agent", create_agent)
    monkeypatch.setattr(validation, "get_chat_model", lambda: validator)
    monkeypatch.setattr(flow, "planner_node", fake_planner)
    return calls, validator


def tool_exchange(response, status="success"):
    return [
        AIMessage(content="", tool_calls=[{"name": "catalog", "args": {}, "id": "catalog-1"}]),
        ToolMessage(
            content="Serviço: Instalar câmera; caminho: Catálogo > Câmeras",
            name="catalog",
            tool_call_id="catalog-1",
            status=status,
        ),
        AIMessage(content=response),
    ]


def test_retries_promise_and_publishes_only_completed_answer(monkeypatch):
    answer = "O serviço é Instalar câmera. Caminho: Catálogo > Câmeras."
    calls, validator = install_agent(
        monkeypatch,
        [[AIMessage(content="Estou consultando o catálogo. Aguarde.")], tool_exchange(answer)],
        [verdict("retry", feedback="Consulte o catálogo e apresente o serviço."), verdict()],
    )
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="Quero instalar uma câmera")]}))

    assert result["response"] == answer
    assert [message.content for message in result["messages"]] == ["Quero instalar uma câmera", answer]
    assert len(calls) == 2
    assert "Consulte o catálogo e apresente o serviço." in calls[1][1]
    assert validator.evidence[0]["tool_results"] == []
    assert validator.evidence[1]["tool_results"][0]["name"] == "catalog"
    assert result["attempt_messages"] == result["tool_results"] == []


def test_stops_after_two_additional_attempts(monkeypatch):
    calls, _ = install_agent(
        monkeypatch, [[AIMessage(content="Vou consultar.")] for _ in range(3)], [verdict("retry") for _ in range(3)]
    )
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="Procure uma câmera")]}))

    assert len(calls) == 3
    assert result["response"] == validation.FAILURE_RESPONSE
    assert len(result["messages"]) == 2
    assert result["retry_count"] == 2


def test_missing_tool_evidence_overrides_complete_verdict(monkeypatch):
    calls, _ = install_agent(
        monkeypatch,
        [[AIMessage(content="O serviço é Instalar câmera.")] for _ in range(3)],
        [verdict() for _ in range(3)],
    )
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="Procure uma câmera")]}))
    assert len(calls) == 3
    assert result["response"] == validation.FAILURE_RESPONSE


def test_reuses_tool_results_when_retry_only_needs_to_present_answer(monkeypatch):
    answer = "Encontrei Instalar câmera em Catálogo > Câmeras."
    calls, validator = install_agent(
        monkeypatch,
        [tool_exchange("Vou listar os resultados."), [AIMessage(content=answer)]],
        [verdict("retry", feedback="Apresente o resultado já obtido."), verdict()],
    )
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="Procure uma câmera")]}))
    assert result["response"] == answer
    assert any(isinstance(message, ToolMessage) for message in calls[1][0])
    assert validator.evidence[0]["tool_results"] == validator.evidence[1]["tool_results"]


@pytest.mark.parametrize(
    "status,answer",
    [
        ("clarification", "Em qual unidade você precisa instalar a câmera?"),
        ("limitation", "Não consegui consultar o catálogo porque a consulta falhou."),
        ("complete", "Olá! Posso ajudar a consultar o catálogo."),
    ],
)
def test_allows_clarification_limitation_and_conversation_without_tools(monkeypatch, status, answer):
    calls, _ = install_agent(monkeypatch, [[AIMessage(content=answer)]], [verdict(status, requires_tool=False)])
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="Olá")]}))
    assert result["response"] == answer
    assert len(calls) == 1


def test_failed_tool_is_not_evidence_of_completed_lookup(monkeypatch):
    calls, _ = install_agent(
        monkeypatch,
        [tool_exchange("Nenhum serviço encontrado.", status="error") for _ in range(3)],
        [verdict() for _ in range(3)],
    )
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="Procure uma câmera")]}))
    assert result["response"] == validation.FAILURE_RESPONSE
    assert len(calls) == 3


def test_validation_failure_never_releases_candidate_or_repeats_action(monkeypatch):
    calls, _ = install_agent(monkeypatch, [tool_exchange("Resposta não validada")], [RuntimeError("validator offline")])
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="Procure uma câmera")]}))
    assert result["response"] == "Não consegui verificar o resultado do seu pedido nesta tentativa."
    assert len(calls) == 1
    assert "Resposta não validada" not in str(result["messages"])


def test_catalog_listing_also_passes_through_react_and_validation(monkeypatch):
    class Catalog:
        name = "list_services_with_done_examples"

        async def ainvoke(self, args):
            return json.dumps({"services": [{"name": "Câmera", "menu_path": ["Catálogo", "Câmera"]}]})

    catalog = json.dumps({"services": [{"name": "Câmera", "menu_path": ["Catálogo", "Câmera"]}]})
    calls, validator = install_agent(
        monkeypatch,
        [[ToolMessage(content=catalog, name=Catalog.name, tool_call_id="catalog"), AIMessage(content="")]],
        [verdict()],
        tools=[Catalog()],
    )
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="Liste os serviços")]}))
    assert "1. Câmera" in result["response"]
    assert len(calls) == len(validator.evidence) == 1


def test_checkpoint_resets_retries_and_evidence_each_turn(monkeypatch):
    answer = "Encontrei Instalar câmera."
    calls, validator = install_agent(
        monkeypatch,
        [
            tool_exchange("Vou apresentar os serviços."),
            [AIMessage(content=answer)],
            [AIMessage(content="Vou consultar.")],
            [AIMessage(content="Vou consultar.")],
            [AIMessage(content="Vou consultar.")],
        ],
        [verdict("retry"), verdict(), verdict(), verdict(), verdict()],
    )
    graph = flow.build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": "conversation"}}

    async def run():
        first = await graph.ainvoke({"messages": [HumanMessage(content="Procure uma câmera")]}, config)
        second = await graph.ainvoke({"messages": [HumanMessage(content="Procure outro serviço")]}, config)
        return first, second

    first, second = asyncio.run(run())
    assert first["response"] == answer
    assert second["response"] == validation.FAILURE_RESPONSE
    assert len(calls) == 5
    assert all(evidence["tool_results"] == [] for evidence in validator.evidence[2:])
    assert len(second["messages"]) == 4


def test_confirmation_is_validated_with_pending_request_in_history(monkeypatch):
    answer = "Encontrei Instalar câmera."
    _, validator = install_agent(
        monkeypatch, [[AIMessage(content="Estou consultando.")], tool_exchange(answer)], [verdict("retry"), verdict()]
    )
    result = asyncio.run(
        flow.build_graph().ainvoke(
            {
                "messages": [
                    HumanMessage(content="Não encontrei esse serviço"),
                    AIMessage(content="Vou listar os serviços disponíveis."),
                    HumanMessage(content="Ótimo"),
                ]
            }
        )
    )
    assert result["response"] == answer
    assert validator.evidence[0]["history"][-1]["content"] == "Ótimo"
    assert validator.evidence[0]["history"][-2]["content"] == "Vou listar os serviços disponíveis."


def test_summary_runs_only_after_validated_final_answer(monkeypatch):
    monkeypatch.setenv("RSA_MEMORY_MAX_MESSAGES", "1")
    answer = "Encontrei Instalar câmera."
    install_agent(
        monkeypatch, [[AIMessage(content="Vou consultar.")], tool_exchange(answer)], [verdict("retry"), verdict()]
    )
    summaries = []

    async def summarize(state):
        summaries.append([message.content for message in state["messages"]])
        return {"summary": "Concluído"}

    monkeypatch.setattr(flow, "summarize_node", summarize)
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="Procure uma câmera")]}))
    assert summaries == [["Procure uma câmera", answer]]
    assert result["response"] == answer
