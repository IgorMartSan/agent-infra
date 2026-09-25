"""Contrato HTTP para submissão de mensagens."""

import os
from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status

from dependencies import get_message_service
from schemas.message import MessageRequest, MessageResponse
from service.conversation_lock import ConversationLockUnavailable
from service.message_service import AgentUnavailable, MessageService, MessageUnavailable
from service.queue_threshold import QueueOverloaded

router = APIRouter()


@router.post(
    '',
    response_model=MessageResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary='Enviar mensagem para um agente',
    responses={
        409: {'description': 'Conversa ocupada.'},
        503: {'description': 'Agente ou infraestrutura indisponível.'},
    },
)
def send_message(
    request: MessageRequest,
    service: Annotated[MessageService, Depends(get_message_service)],
) -> MessageResponse:
    message_id = str(uuid4())
    try:
        service.send({'message_id': message_id, **request.model_dump(mode='json')})
    except ConversationLockUnavailable as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    except AgentUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error), headers={'Retry-After': '30'}) from error
    except QueueOverloaded as error:
        raise HTTPException(
            status_code=503, detail=str(error), headers={'Retry-After': os.getenv('QUEUE_RETRY_AFTER_SECONDS', '30')}
        ) from error
    except MessageUnavailable as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    return MessageResponse(message_id=message_id, status='ACCEPTED')
