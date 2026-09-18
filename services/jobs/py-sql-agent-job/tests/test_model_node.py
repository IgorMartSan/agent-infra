from types import SimpleNamespace

import pytest

from graph import nodes


class FakeAgent:
    def __init__(self, content: object) -> None:
        self.content = content
        self.input = None
        self.calls = 0
        self.updates = []

    def get_state(self, config: dict) -> SimpleNamespace:
        return SimpleNamespace(values={"messages": []})

    def update_state(self, config: dict, values: dict) -> None:
        self.updates.append(values)

    def invoke(self, payload: dict, config: dict | None = None) -> dict:
        self.calls += 1
        self.input = payload
        return {"messages": [SimpleNamespace(id="answer-1", content=self.content)]}


def test_receive_message_invokes_sql_agent_with_user_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = FakeAgent("  Resposta do modelo  ")
    monkeypatch.setattr(nodes, "build_sql_agent", lambda: agent)

    result = nodes.receive_message({"message": "Olá", "response": ""})

    assert result == {"response": "Resposta do modelo"}
    assert agent.input is not None
    assert agent.input["messages"][0]["content"] == "Olá"


def test_receive_message_rejects_empty_model_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agent = FakeAgent("  ")
    monkeypatch.setattr(nodes, "build_sql_agent", lambda: agent)

    with pytest.raises(RuntimeError, match="resposta vazia"):
        nodes.receive_message({"message": "Olá", "response": ""})

    assert agent.calls == 2


def test_receive_message_retries_empty_model_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RecoveringAgent(FakeAgent):
        def invoke(self, payload: dict, config: dict | None = None) -> dict:
            self.content = "  " if self.calls == 0 else "Resposta recuperada"
            return super().invoke(payload, config)

    agent = RecoveringAgent("")
    monkeypatch.setattr(nodes, "build_sql_agent", lambda: agent)

    assert nodes.receive_message({"message": "Olá", "response": ""}) == {"response": "Resposta recuperada"}
    assert agent.calls == 2


def test_receive_message_uses_tool_result_when_final_model_message_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class AgentWithToolResult:
        def get_state(self, config: dict) -> SimpleNamespace:
            return SimpleNamespace(values={"messages": []})

        def update_state(self, config: dict, values: dict) -> None:
            pass

        def invoke(self, payload: dict, config: dict | None = None) -> dict:
            return {
                "messages": [
                    SimpleNamespace(type="tool", name="sql_db_list_tables", content="orders, users"),
                    SimpleNamespace(
                        id="answer-1", content="", response_metadata={"finish_reason": "stop"}, tool_calls=[]
                    ),
                ]
            }

    class FinalModel:
        def invoke(self, messages: list) -> SimpleNamespace:
            assert "orders, users" in messages[1][1]
            return SimpleNamespace(content="Tabelas: orders e users.")

    monkeypatch.setattr(nodes, "build_sql_agent", AgentWithToolResult)
    monkeypatch.setattr(nodes, "get_chat_model", FinalModel)

    assert nodes.receive_message({"message": "Quais as tabelas?", "response": ""}) == {
        "response": "Tabelas: orders e users."
    }
