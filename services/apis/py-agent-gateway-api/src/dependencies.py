"""Cria os adaptadores por requisição e fecha os clientes ao terminar."""

import os
from typing import Annotated

from fastapi import Depends

from infra.rabbitmq.connection import RabbitMQConnection
from infra.rabbitmq.producer import RabbitMQProducer
from infra.rabbitmq.queue_repository import QueueRepository
from infra.redis.agent_repository import AgentRepository
from infra.redis.connection import RedisConnection
from service.conversation_lock import ConversationLock
from service.message_service import MessageService
from service.queue_threshold import QueueThreshold


def get_redis_client():
    connection = RedisConnection()
    try:
        yield connection.get_client()
    finally:
        connection.close()


def get_agent_repository(redis_client: Annotated[object, Depends(get_redis_client)]):
    return AgentRepository(redis_client, os.getenv("AGENT_ONLINE_KEY_PREFIX", "agent:online:"))


def get_message_service(
    redis_client: Annotated[object, Depends(get_redis_client)],
    agents: Annotated[AgentRepository, Depends(get_agent_repository)],
):
    # Uma conexão por requisição evita compartilhar o cliente Pika entre threads
    # e evita reutilizar uma conexão encerrada pelo broker enquanto a API estava ociosa.
    rabbitmq = RabbitMQConnection()
    try:
        yield MessageService(
            producer=RabbitMQProducer(rabbitmq),
            agents=agents,
            conversation_lock=ConversationLock(
                redis_client, ttl_seconds=int(os.getenv("CONVERSATION_LOCK_TTL_SECONDS", "300"))
            ),
            queue_threshold=QueueThreshold(
                QueueRepository(rabbitmq).message_count, max_messages=int(os.getenv("QUEUE_MAX_MESSAGES", "100"))
            ),
            exchange=os.getenv("RABBITMQ_EXCHANGE", "agent.requests"),
        )
    finally:
        rabbitmq.close()
