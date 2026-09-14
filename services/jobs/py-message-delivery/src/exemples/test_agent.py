from typing import Any


class TestAgent:
    """Agente padrão que confirma e concatena as mensagens recebidas."""

    name = "agent1"

    def respond(self, _chat_id: str, messages: list[dict[str, Any]]) -> str:
        received_messages = [
            str(message.get("message", "")).strip() for message in messages if str(message.get("message", "")).strip()
        ]
        if not received_messages:
            return "Oi, sou o agente 1. Nenhuma mensagem foi recebida."
        return "Oi, sou o agente 1. As suas mensagens foram: " + " | ".join(received_messages)
