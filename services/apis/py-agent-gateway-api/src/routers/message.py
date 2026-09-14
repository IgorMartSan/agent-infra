import logging
import os
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from infra.rabbitmq.connection import rabbitmq
from infra.rabbitmq.producer import RabbitMQProducer
from schemas.message import (
    MessageRequest,
    MessageResponse,
)
from service.message_service import MessageService

router = APIRouter()
logger = logging.getLogger(__name__)
message_service = MessageService(
    RabbitMQProducer(rabbitmq),
    exchange=os.getenv('RABBITMQ_EXCHANGE', 'agent.requests'),
)


@router.post(
    '',
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary='Enviar mensagem para um agente',
    description=(
        'Recebe uma mensagem de uma aplicação cliente e a encaminha para '
        'processamento assíncrono através do RabbitMQ. '
        'A API retorna imediatamente após aceitar a mensagem.'
    ),
    responses={
        202: {
            'description': 'Mensagem aceita para processamento.',
        },
        422: {
            'description': 'Payload inválido.',
        },
        503: {
            'description': 'RabbitMQ indisponível.',
        },
    },
)
def send_message(
    request: MessageRequest,
) -> MessageResponse:
    message_id = str(uuid4())
    message = {
        'message_id': message_id,
        **request.model_dump(mode='json'),
    }

    try:
        message_service.send(message)
    except Exception as exc:
        logger.exception('Falha ao publicar a mensagem %s no RabbitMQ', message_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='RabbitMQ indisponível para receber a mensagem.',
        ) from exc

    return MessageResponse(
        message_id=message_id,
        status='ACCEPTED',
    )
