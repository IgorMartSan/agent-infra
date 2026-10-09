import asyncio
import json
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from agents.langchain_agents.rsa_flow import graph as flow
from agents.langchain_agents.rsa_flow import nodes, planner, validation

pytestmark = pytest.mark.usefixtures("rsa_env")


def plan(decision="tools", question="Quero instalar uma câmera", selected=None):
    return {
        "decision": decision,
        "normalized_question": question,
        "selected_tools": (["catalog"] if decision == "tools" else []) if selected is None else selected,
        "steps": [
            "Consulte serviços compatíveis e apresente o caminho real."
            if decision == "tools"
            else "Responda pelo contexto ou informe a limitação."
        ],
    }


@pytest.fixture
def harness(monkeypatch):
    class Tool:
        def __init__(self, name, description, args):
            self.name, self.description, self.args = name, description, args
            self.calls = 0

        async def ainvoke(self, args):
            self.calls += 1
            return json.dumps({"services": [{"name": "Câmera", "menu_path": ["Catálogo", "Câmera"]}]})

    catalog = Tool(
        "catalog", "Descobre serviços e orienta sobre o formulário. Somente leitura.", {"query": {"type": "string"}}
    )
    other = Tool("other", "Consulta informações de outro sistema", {})
    tools = [catalog, other]
    planned = [plan()]
    contexts = []
    executions = []
    responses = []
    verdicts = []

    class Client:
        @asynccontextmanager
        async def session(self, name):
            yield object()

    async def load_tools(session):
        return tools

    class Model:
        def with_structured_output(self, schema, method):
            assert schema is planner.PlannerDecision
            assert method == "function_calling"

            class Structured:
                async def ainvoke(self, messages):
                    contexts.append(json.loads(messages[-1].content))
                    result = planned.pop(0)
                    if isinstance(result, Exception):
                        raise result
                    return result

            return Structured()

        async def ainvoke(self, messages):
            responses.append(messages)
            return AIMessage(content="Você informou seu nome como João.")

    def create_agent(**kwargs):
        class Agent:
            async def ainvoke(self, payload, config):
                executions.append((kwargs, payload))
                if not kwargs["tools"]:
                    if "O planejamento falhou" in kwargs["system_prompt"]:
                        answer = "Não consegui analisar seu pedido nesta tentativa."
                    elif "O plano indica uma capacidade indisponível" in kwargs["system_prompt"]:
                        answer = "Não consigo criar solicitações com as capacidades disponíveis."
                    else:
                        answer = "Você informou seu nome como João."
                    return {"messages": [*payload["messages"], AIMessage(content=answer)]}
                return {
                    "messages": [
                        *payload["messages"],
                        AIMessage(content="", tool_calls=[{"name": "catalog", "args": {}, "id": "tool-1"}]),
                        ToolMessage(
                            content="Serviço: Câmera; caminho: Catálogo > Câmera", name="catalog", tool_call_id="tool-1"
                        ),
                        AIMessage(content="Encontrei Câmera em Catálogo > Câmera."),
                    ]
                }

        return Agent()

    class Validator:
        def with_structured_output(self, schema, method):
            return self

        async def ainvoke(self, messages):
            if verdicts:
                return verdicts.pop(0)
            return validation.ResponseValidation(status="complete", requires_tool=False, feedback="")

    monkeypatch.setattr(nodes, "get_mcp_client", Client)
    monkeypatch.setattr(nodes, "load_mcp_tools", load_tools)
    monkeypatch.setattr(nodes, "get_chat_model", Model)
    monkeypatch.setattr(nodes, "create_agent", create_agent)
    monkeypatch.setattr(validation, "get_chat_model", Validator)
    return {
        "planned": planned,
        "contexts": contexts,
        "executions": executions,
        "responses": responses,
        "tools": tools,
        "catalog": catalog,
        "other": other,
        "verdicts": verdicts,
    }


def test_planner_reads_real_schemas_without_executing_tools(harness):
    result = asyncio.run(planner.planner_node({"messages": [HumanMessage(content="quero instala uma camera")]}))
    assert result["plan"]["decision"] == "tools"
    inventory = harness["contexts"][0]["tools_inventory"]
    assert "catalog" in inventory and "other" in inventory
    assert "Somente leitura" in inventory and '"query"' in inventory
    assert harness["catalog"].calls == harness["other"].calls == 0
    assert harness["executions"] == harness["responses"] == []
    assert "messages" not in result and "response" not in result


def test_tools_route_filters_selection_and_silently_corrects_question(harness):
    original = "quero instala uma camera"
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content=original)]}))
    kwargs, payload = harness["executions"][0]
    assert [tool.name for tool in kwargs["tools"]] == ["catalog"]
    assert payload["messages"][-1].content == "Quero instalar uma câmera"
    assert "Consulte serviços compatíveis" in kwargs["system_prompt"]
    assert result["messages"][0].content == original
    assert result["response"] == "Encontrei Câmera em Catálogo > Câmera."


def test_respond_plan_uses_react_without_tools(harness):
    harness["planned"][:] = [plan("respond", "Qual é o meu nome?")]
    result = asyncio.run(
        flow.build_graph().ainvoke(
            {
                "messages": [
                    HumanMessage(content="Meu nome é João"),
                    AIMessage(content="Entendido"),
                    HumanMessage(content="qual e meu nome?"),
                ]
            }
        )
    )
    assert result["response"] == "Você informou seu nome como João."
    assert len(harness["executions"]) == 1
    assert harness["executions"][0][0]["tools"] == []
    assert harness["responses"] == []
    assert harness["catalog"].calls == harness["other"].calls == 0


def test_finish_plan_always_passes_through_react_and_validation(harness):
    harness["planned"][:] = [plan("finish", "Crie uma solicitação no RSA")]
    result = asyncio.run(
        flow.build_graph().ainvoke({"messages": [HumanMessage(content="Crie uma solicitação no RSA")]})
    )
    assert result["response"] == "Não consigo criar solicitações com as capacidades disponíveis."
    assert len(harness["executions"]) == 1
    assert harness["executions"][0][0]["tools"] == []
    assert harness["responses"] == []
    assert harness["catalog"].calls == harness["other"].calls == 0
    assert len(result["messages"]) == 2


def test_unknown_tool_fails_closed(harness):
    harness["planned"][:] = [plan(selected=["invented_tool"])]
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="Procure uma câmera")]}))
    assert "Não consegui analisar" in result["response"]
    assert result["planning_error"] is True
    assert len(harness["executions"]) == 1
    assert harness["executions"][0][0]["tools"] == []
    assert harness["responses"] == []


@pytest.mark.parametrize("decision,selected", [("tools", []), ("respond", ["catalog"]), ("finish", ["catalog"])])
def test_structured_plan_rejects_inconsistent_selection(decision, selected):
    with pytest.raises(ValidationError):
        planner.PlannerDecision.model_validate(plan(decision, selected=selected))


def test_empty_inventory_allows_conversation_but_not_invented_tools(harness):
    harness["tools"].clear()
    harness["planned"][:] = [plan("respond", "Qual é o meu nome?")]
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="Qual é o meu nome?")]}))
    assert result["planning_error"] is False
    assert len(harness["executions"]) == 1
    assert harness["executions"][0][0]["tools"] == []
    assert harness["contexts"][0]["tools_inventory"].endswith("[]")


def test_context_includes_summary_confirmation_and_validation_feedback(harness):
    asyncio.run(
        planner.planner_node(
            {
                "messages": [AIMessage(content="Vou listar os serviços."), HumanMessage(content="Ótimo")],
                "summary": "O usuário procura serviços de câmeras.",
                "retry_feedback": "Apresente os resultados já obtidos.",
                "tool_results": [{"name": "catalog", "status": "success", "content": "Câmera"}],
            }
        )
    )
    context = harness["contexts"][0]
    assert context["history"][-1]["content"] == "Ótimo"
    assert context["summary"] == "O usuário procura serviços de câmeras."
    assert context["retry_feedback"] == "Apresente os resultados já obtidos."
    assert context["tool_results"][0]["content"] == "Câmera"


def test_model_failure_does_not_claim_missing_capability(harness):
    harness["planned"][:] = [RuntimeError("model unavailable")]
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="Procure uma câmera")]}))
    assert "Não consegui analisar" in result["response"]
    assert "Não consigo atender" not in result["response"]
    assert len(harness["executions"]) == 1
    assert harness["executions"][0][0]["tools"] == []


def test_execution_rechecks_tools_if_inventory_changes(harness):
    harness["tools"].clear()
    with pytest.raises(ValueError, match="ferramentas disponíveis"):
        asyncio.run(nodes.chat_node({"messages": [HumanMessage(content="Procure uma câmera")], "plan": plan()}))
    assert harness["executions"] == []


def test_plan_is_recomputed_after_new_turn(harness):
    harness["planned"][:] = [plan("finish", "Crie uma solicitação"), plan("respond", "Qual é o meu nome?")]
    graph = flow.build_graph(InMemorySaver())
    config = {"configurable": {"thread_id": "planner-conversation"}}

    async def run():
        await graph.ainvoke({"messages": [HumanMessage(content="Crie uma solicitação")]}, config)
        return await graph.ainvoke({"messages": [HumanMessage(content="Qual é o meu nome?")]}, config)

    result = asyncio.run(run())
    assert len(harness["contexts"]) == 2
    assert result["plan"]["decision"] == "respond"
    assert len(harness["executions"]) == 2
    assert harness["responses"] == []
    assert len(result["messages"]) == 4


def test_validation_replans_respond_route_into_tools(harness):
    harness["planned"][:] = [plan("respond"), plan()]
    harness["verdicts"][:] = [
        validation.ResponseValidation(status="retry", requires_tool=True, feedback="Consulte o catálogo de câmeras.")
    ]
    result = asyncio.run(flow.build_graph().ainvoke({"messages": [HumanMessage(content="quero instala uma camera")]}))
    assert len(harness["contexts"]) == 2
    assert harness["contexts"][1]["retry_feedback"] == "Consulte o catálogo de câmeras."
    assert len(harness["executions"]) == 2
    assert harness["responses"] == []
    assert result["response"] == "Encontrei Câmera em Catálogo > Câmera."
    assert len(result["messages"]) == 2
