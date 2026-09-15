from collections.abc import Mapping
from typing import Any

from graph.graph import graph


class InvalidMessageError(ValueError):
    """Indica uma mensagem que deve ser descartada, sem nova tentativa."""


def process_agent_message(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Executa a mensagem no agente e monta o evento de resposta."""
    if not isinstance(payload, Mapping):
        raise InvalidMessageError("O payload deve ser um objeto JSON.")

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise InvalidMessageError("O campo 'message' deve ser uma string não vazia.")

    result = graph.invoke(
        {
            "message": message.strip(),
            "response": "",
        }
    )
    response = result.get("response")
    if not isinstance(response, str):
        raise TypeError("O agente não retornou uma resposta válida.")

    return {
        **dict(payload),
        "status": "PROCESSED",
        "response": response,
    }
