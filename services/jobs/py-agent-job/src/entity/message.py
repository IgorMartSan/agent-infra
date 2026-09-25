"""Mensagem recebida do gateway e encaminhada ao agente."""

from dataclasses import dataclass


class InvalidMessageError(ValueError):
    """O RabbitMQ recebeu uma mensagem que não pode ser processada."""


@dataclass(frozen=True)
class AgentMessage:
    application_id: str
    message_id: str
    agent_id: str
    message: str
    chat_id: str | None = None
    user_id: str | None = None

    @classmethod
    def from_payload(cls, payload: dict) -> "AgentMessage":
        if not isinstance(payload, dict):
            raise InvalidMessageError("A mensagem deve ser um objeto JSON.")
        try:
            message = cls(
                application_id=payload["application_id"],
                message_id=payload["message_id"],
                agent_id=payload["agent_id"],
                message=payload["message"],
                chat_id=payload.get("chat_id") or payload.get("conversation_id"),
                user_id=payload.get("user_id"),
            )
        except KeyError as error:
            raise InvalidMessageError(f"Campo obrigatório ausente: {error.args[0]}") from error
        if not all(
            isinstance(value, str) and value.strip()
            for value in (
                message.application_id,
                message.message_id,
                message.agent_id,
                message.message,
            )
        ):
            raise InvalidMessageError("IDs obrigatórios e texto da mensagem devem ser strings não vazias.")
        return message
