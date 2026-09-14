import pytest

from processor import InvalidMessageError, process_agent_message


def test_processes_message_and_preserves_request_context() -> None:
    payload = {
        "message_id": "message-123",
        "application_id": "erp",
        "agent_id": "agent-suporte",
        "message": "Olá",
    }

    result = process_agent_message(payload)

    assert result["message_id"] == "message-123"
    assert result["application_id"] == "erp"
    assert result["agent_id"] == "agent-suporte"
    assert result["message"] == "Olá"
    assert result["status"] == "PROCESSED"
    assert "Eu recebi a mensagem: Olá" in result["response"]


@pytest.mark.parametrize("payload", [{}, {"message": ""}, {"message": "   "}, {"message": None}])
def test_rejects_missing_or_empty_message(payload: dict) -> None:
    with pytest.raises(InvalidMessageError):
        process_agent_message(payload)
