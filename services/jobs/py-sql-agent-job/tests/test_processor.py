from unittest.mock import Mock

import pytest

import processor
from graph.memory import thread_id_for
from processor import InvalidMessageError


def test_processes_message_and_preserves_request_context(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "message_id": "message-123",
        "application_id": "erp",
        "chat_id": "chat-1",
        "agent_id": "agent-suporte",
        "message": "Olá",
    }

    invoke = Mock(return_value={"response": "Resposta gerada pelo Gemma 4"})
    monkeypatch.setattr(processor.graph, "invoke", invoke)

    result = processor.process_agent_message(payload)

    assert result["message_id"] == "message-123"
    assert result["application_id"] == "erp"
    assert result["agent_id"] == "agent-suporte"
    assert result["message"] == "Olá"
    assert result["status"] == "PROCESSED"
    assert result["response"] == "Resposta gerada pelo Gemma 4"
    invoke.assert_called_once_with({"message": "Olá", "response": "", "thread_id": thread_id_for(payload)})


@pytest.mark.parametrize("payload", [{}, {"message": ""}, {"message": "   "}, {"message": None}])
def test_rejects_missing_or_empty_message(payload: dict) -> None:
    with pytest.raises(InvalidMessageError):
        processor.process_agent_message(payload)
