"""Processador de mensagens do agente unificado — valida payload e executa o grafo dinâmico."""
import asyncio
import os
from collections.abc import Mapping
from typing import Any

from agents.registry import get_agent_graph


class InvalidMessageError(ValueError):
    """Indica uma mensagem que deve ser descartada, sem nova tentativa."""


class AgentProcessingError(RuntimeError):
    """Indica que o agente falhou ao processar uma mensagem válida.

    A mensagem é descartada sem requeue, pois o usuário já foi
    notificado do erro via evento message.failed no Pub/Sub.
    """


def process_agent_message(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Executa a mensagem no agente selecionado via AGENT_ID e monta o evento de resposta."""
    if not isinstance(payload, Mapping):
        raise InvalidMessageError("O payload deve ser um objeto JSON.")

    message = payload.get("message")
    if not isinstance(message, str) or not message.strip():
        raise InvalidMessageError("O campo 'message' deve ser uma string não vazia.")

    agent_id = os.getenv("AGENT_ID")
    if not agent_id:
        raise AgentProcessingError("AGENT_ID não está definido no ambiente.")

    try:
        graph = get_agent_graph(agent_id)
    except RuntimeError as error:
        raise AgentProcessingError(str(error)) from error

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
            f"O agente '{agent_id}' não conseguiu processar a mensagem: {error}"
        ) from error

    response = result.get("response")
    if not isinstance(response, str) or not response.strip():
        raise AgentProcessingError(f"O agente '{agent_id}' não retornou uma resposta válida.")

    return {
        **dict(payload),
        "status": "PROCESSED",
        "response": response,
    }