"""Processador de mensagens do agente RSA — valida payload e executa o grafo."""

import asyncio
from collections.abc import Mapping
from typing import Any

from graph.graph import graph


class InvalidMessageError(ValueError):
    """Indica uma mensagem que deve ser descartada, sem nova tentativa."""


class AgentProcessingError(RuntimeError):
    """Indica que o agente falhou ao processar uma mensagem válida.

    A mensagem é descartada sem requeue, pois o usuário já foi
    notificado do erro via evento message.failed no Pub/Sub.
    """


def process_agent_message(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Executa a mensagem no agente RSA e monta o evento de resposta."""
    if not isinstance(payload, Mapping):
        raise InvalidMessageError("O payload deve ser um objeto JSON.")

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise InvalidMessageError("O campo 'message' deve ser uma string não vazia.")

    try:
        result = asyncio.run(
            graph.ainvoke(
                {
                    "message": message.strip(),
                    "response": "",
                    "thread_id": payload.get("thread_id", ""),
                }
            )
        )
    except Exception as error:
        raise AgentProcessingError(
            f"O agente RSA não conseguiu processar a mensagem: {error}"
        ) from error

    response = result.get("response")
    if not isinstance(response, str) or not response.strip():
        raise AgentProcessingError("O agente RSA não retornou uma resposta válida.")

    return {
        **dict(payload),
        "status": "PROCESSED",
        "response": response,
    }