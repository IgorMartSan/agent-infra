from types import SimpleNamespace

import pytest

from graph import nodes


class FakeChatModel:
    def __init__(self, content: object) -> None:
        self.content = content
        self.messages = None

    def invoke(self, messages: list) -> SimpleNamespace:
        self.messages = messages
        return SimpleNamespace(content=self.content)


def test_receive_message_calls_model_with_system_and_human_messages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model = FakeChatModel("  Resposta do modelo  ")
    monkeypatch.setattr(nodes, "get_chat_model", lambda: model)

    result = nodes.receive_message({"message": "Olá", "response": ""})

    assert result == {"response": "Resposta do modelo"}
    assert model.messages is not None
    assert model.messages[0].type == "system"
    assert model.messages[1].type == "human"
    assert model.messages[1].content == "Olá"


def test_receive_message_rejects_empty_model_response(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(nodes, "get_chat_model", lambda: FakeChatModel("  "))

    with pytest.raises(RuntimeError, match="resposta vazia"):
        nodes.receive_message({"message": "Olá", "response": ""})
