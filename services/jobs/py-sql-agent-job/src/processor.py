from collections.abc import Mapping
from typing import Any

from graph.graph import graph
from graph.memory import thread_id_for


class InvalidMessageError(ValueError):
    """Indica uma mensagem que deve ser descartada, sem nova tentativa."""


class AgentProcessingError(RuntimeError):
    """Indica que o agente falhou ao processar uma mensagem válida.

    A mensagem é descartada sem requeue, pois o usuário já foi
    notificado do erro via evento message.failed no Pub/Sub.
    """


def process_agent_message(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Executa a mensagem no agente e monta o evento de resposta."""
    if not isinstance(payload, Mapping):
        raise InvalidMessageError("O payload deve ser um objeto JSON.")

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise InvalidMessageError("O campo 'message' deve ser uma string não vazia.")

    try:
        result = graph.invoke(
            {
                "message": message.strip(),
                "response": "",
                "thread_id": thread_id_for(payload),
            }
        )
    except Exception as error:
        # O agente falhou (modelo fora do ar, erro no banco, etc.).
        # O main.py captura AgentProcessingError, notifica o usuário
        # via message.failed no Pub/Sub e descarta a mensagem.
        raise AgentProcessingError(f"O agente não conseguiu processar a mensagem: {error}") from error

    response = result.get("response")
    if not isinstance(response, str):
        raise AgentProcessingError("O agente não retornou uma resposta válida.")

    return {
        **dict(payload),
        "status": "PROCESSED",
        "response": response,
    }
