from typing import Literal

from pydantic import BaseModel, Field


class DeliverySchema(BaseModel):
    type: Literal[
        'WEBSOCKET',
        'HTTP',
        'GOOGLE_CHAT',
        'NONE',
    ] = Field(
        description='Define como a resposta do agente será entregue.',
        examples=['WEBSOCKET'],
    )

    target: str | None = Field(
        default=None,
        description='Destino lógico para entregas HTTP ou integrações externas.',
        examples=['erp-callback'],
    )

    channel: str | None = Field(
        default=None,
        description='Canal usado para entrega via WebSocket.',
        examples=['erp:chat:456'],
    )

    space_id: str | None = Field(
        default=None,
        description='Identificador do espaço do Google Chat.',
        examples=['spaces/AAAA123'],
    )


class MessageRequest(BaseModel):
    application_id: str = Field(
        description='Identificador da aplicação de origem.',
        examples=['erp'],
    )

    user_id: str | None = Field(
        default=None,
        description='Identificador do usuário na aplicação de origem.',
        examples=['user-123'],
    )

    chat_id: str | None = Field(
        default=None,
        description='Identificador do chat ou conversa na aplicação de origem.',
        examples=['chat-456'],
    )

    agent_id: str = Field(
        description='Identificador do agente que deverá processar a mensagem.',
        examples=['agent-suporte'],
    )

    message: str = Field(
        description='Conteúdo enviado para o agente.',
        examples=['Verifique o status do chamado 900.'],
    )

    metadata: dict[str, object] | None = Field(
        default=None,
        description='Metadados opcionais fornecidos pela aplicação de origem.',
        examples=[{'source': 'message-simulator'}],
    )

    delivery: DeliverySchema | None = Field(
        default=None,
        description='Configuração de entrega da resposta do agente.',
    )


class MessageResponse(BaseModel):
    message_id: str = Field(
        description='Identificador único da mensagem.',
        examples=['550e8400-e29b-41d4-a716-446655440000'],
    )

    status: str = Field(
        description='Status inicial da mensagem.',
        examples=['ACCEPTED'],
    )
