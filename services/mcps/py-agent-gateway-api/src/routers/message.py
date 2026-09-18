import logging
import os
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from infra.rabbitmq.connection import rabbitmq
from infra.rabbitmq.producer import RabbitMQProducer
from infra.redis.connection import RedisConnection
from routers.agents import require_available_agent
from schemas.message import (
    MessageRequest,
    MessageResponse,
)
from service.conversation_lock import ConversationLock, ConversationLockUnavailable
from service.message_service import MessageService
from service.queue_threshold import QueueOverloaded, QueueThreshold

router = APIRouter()
logger = logging.getLogger(__name__)
redis_connection = RedisConnection()
conversation_lock = ConversationLock(
    redis_connection.get_client(),
    ttl_seconds=int(os.getenv('CONVERSATION_LOCK_TTL_SECONDS', '300')),
)
message_service = MessageService(
    RabbitMQProducer(rabbitmq),
    exchange=os.getenv('RABBITMQ_EXCHANGE', 'agent.requests'),
)
queue_threshold = QueueThreshold(
    lambda: rabbitmq.channel,
    max_messages=int(os.getenv('QUEUE_MAX_MESSAGES', '100')),
)
queue_retry_after_seconds = int(os.getenv('QUEUE_RETRY_AFTER_SECONDS', '30'))


def queue_name_for(agent_id: str) -> str:
    """Deriva o nome da fila a partir do agent_id, como o MessageService faz."""
    agent_name = agent_id.strip().lower().removesuffix('-agent')
    return f"agent.{agent_name.replace('-', '.')}.requests"


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
        409: {
            'description': 'Já existe uma mensagem em processamento para a conversa.',
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

    # Verificação de disponibilidade: só aceita mensagens para agentes
    # com pelo menos um worker ativo (heartbeat presente no Redis).
    # Se o worker cair, o TTL da chave expira e o agente fica indisponível.
    require_available_agent(request.agent_id)

    # Verificação de sobrecarga: bloqueia a entrada quando a fila do
    # agente atingiu o limite (padrão 100). Devolve 503 com Retry-After
    # para o cliente tentar novamente após alguns segundos.
    try:
        queue_threshold.check(queue_name_for(request.agent_id))
    except QueueOverloaded as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
            headers={'Retry-After': str(queue_retry_after_seconds)},
        ) from exc

    # Validacao de entrada: uma mensagem por conversa por vez.
    # A chave combina application_id + chat_id + agent_id; se ja existir,
    # devolve 409 imediatamente sem publicar no RabbitMQ.
    try:
        conversation_lock.acquire(
            application_id=request.application_id,
            chat_id=request.chat_id,
            agent_id=request.agent_id,
        )
    except ConversationLockUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    try:
        message_service.send(message)
    except Exception as exc:
        # Publicacao falhou: libera o lock para nao travar a conversa ate o TTL.
        conversation_lock.release(
            application_id=request.application_id,
            chat_id=request.chat_id,
            agent_id=request.agent_id,
        )
        logger.exception('Falha ao publicar a mensagem %s no RabbitMQ', message_id)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail='RabbitMQ indisponível para receber a mensagem.',
        ) from exc

    return MessageResponse(
        message_id=message_id,
        status='ACCEPTED',
    )
