from typing import Any, Protocol


class MessageAgent(Protocol):
    """Contrato de um agente capaz de responder grupos de mensagens."""

    name: str

    def respond(self, chat_id: str, messages: list[dict[str, Any]]) -> str:
        """Produz uma resposta para as mensagens recebidas no chat."""
        ...
