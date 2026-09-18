"""Worker de produção do SQLAgent — fluxo: RabbitMQ -> agente -> Redis Pub/Sub.

Estrutura do fluxo (visível em 5 passos dentro de handle_message):

1. O consumer entrega o payload recebido do RabbitMQ.
2. O processor valida o payload e roda o agente (LangGraph + SQLDatabaseToolkit).
3. A resposta é publicada no Redis Pub/Sub no canal da conversa.
4. O ACK confirma o processamento ao RabbitMQ.
5. Se algo falhar, o consumer decide reprocessar ou descartar.

Fora disso, este arquivo cuida apenas do ciclo de vida do worker:
conexões, log, loop de reconexão e desligamento limpo.
"""

import logging
import os
import time

from dotenv import load_dotenv

from infra.rabbitmq.connection import RabbitMQConnection
from infra.rabbitmq.consumer import RabbitMQConsumer
from infra.redis import (
    AgentRegistry,
    AgentResponsePubSubRepository,
    ConversationLock,
    RedisConnection,
)
from processor import AgentProcessingError, InvalidMessageError, process_agent_message

load_dotenv()

logging.basicConfig(
    level=os.environ["LOG_LEVEL"].upper(),
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def build_response_publisher() -> AgentResponsePubSubRepository:
    """Cria o publicador de respostas no Redis Pub/Sub (passo 3)."""
    return AgentResponsePubSubRepository(
        RedisConnection(),
        channel_prefix=os.environ["REDIS_RESPONSE_CHANNEL_PREFIX"],
    )


def run_worker() -> None:
    agent_id = os.environ["AGENT_ID"]
    exchange = os.environ["RABBITMQ_EXCHANGE"]
    queue = os.environ["RABBITMQ_QUEUE"]
    routing_key = os.environ["RABBITMQ_ROUTING_KEY"]
    prefetch_count = int(os.environ["RABBITMQ_PREFETCH_COUNT"])
    reconnect_delay = float(os.environ["RABBITMQ_RECONNECT_DELAY"])

    redis_connection = RedisConnection()
    response_pubsub = build_response_publisher()
    conversation_lock = ConversationLock(redis_connection.get_client())

    # Registra a disponibilidade do agente no Redis enquanto o worker vive.
    # Se o processo cair, o TTL da chave expira e o gateway para de
    # aceitar mensagens para este agente (nenhum worker ativo).
    agent_registry = AgentRegistry(
        redis_connection.get_client(),
        agent_id,
        ttl_seconds=int(os.environ.get("AGENT_HEARTBEAT_TTL_SECONDS", "30")),
        interval_seconds=float(
            os.environ.get("AGENT_HEARTBEAT_INTERVAL_SECONDS", "10")
        ),
    )
    agent_registry.start()

    def release_lock(payload: dict) -> None:
        """Libera a conversa para a próxima mensagem (remove a chave do gateway)."""
        try:
            conversation_lock.release(
                application_id=payload.get("application_id"),
                chat_id=payload.get("chat_id"),
                agent_id=payload.get("agent_id"),
            )
        except Exception:
            logger.exception(
                "Não foi possível liberar o lock da conversa: message_id=%s",
                payload.get("message_id", "sem-id"),
            )

    def publish_error(payload: dict, reason: str) -> None:
        """Publica o evento de falha no canal da conversa (passo 3, caminho de erro)."""
        conversation_id = payload.get("conversation_id") or payload.get("chat_id")
        try:
            subscribers = response_pubsub.publish_failed(
                application_id=payload.get("application_id"),
                conversation_id=conversation_id,
                message_id=payload.get("message_id"),
                agent_id=payload.get("agent_id"),
                reason=reason,
            )
            logger.info(
                "Falha notificada ao cliente: message_id=%s redis_subscribers=%s",
                payload.get("message_id", "sem-id"),
                subscribers,
            )
        except Exception:
            # Se o Redis também estiver fora, resta o log para investigar.
            logger.exception(
                "Não foi possível notificar o cliente da falha: message_id=%s",
                payload.get("message_id", "sem-id"),
            )

    def handle_message(payload: dict) -> None:
        """Passos 1 a 3 do fluxo, executados para cada mensagem consumida."""
        # Passo 2: valida o payload (message não vazia) e roda o agente.
        # InvalidMessageError => mensagem malformada, será descartada no passo 5.
        # AgentProcessingError => o usuário já foi avisado via message.failed;
        # a mensagem também é descartada, para não gerar eventos de erro repetidos.
        try:
            response = process_agent_message(payload)
        except AgentProcessingError as error:
            publish_error(payload, str(error))
            release_lock(payload)
            # Re-lança para o consumer descartar (sem requeue) e logar a causa.
            raise

        # A persistência PostgreSQL da resposta será adicionada aqui futuramente.

        # Passo 3: publica o evento message.completed no canal da conversa.
        conversation_id = payload.get("conversation_id") or payload.get("chat_id")
        subscribers = response_pubsub.publish_completed(
            application_id=payload.get("application_id"),
            conversation_id=conversation_id,
            message_id=payload.get("message_id"),
            agent_id=payload.get("agent_id"),
            content=response["response"],
        )
        logger.info(
            "Mensagem processada: message_id=%s redis_subscribers=%s",
            payload.get("message_id", "sem-id"),
            subscribers,
        )

        # Libera a conversa para a próxima mensagem somente depois
        # de a resposta ter sido publicada com sucesso.
        release_lock(payload)

    try:
        while True:
            # Cada iteração é uma "vida" da conexão RabbitMQ: abre, consome
            # até cair, fecha e tenta de novo após reconnect_delay.
            connection = RabbitMQConnection()
            consumer = RabbitMQConsumer(connection)

            try:
                logger.info(
                    "Worker aguardando: agent_id=%s exchange=%s fila=%s routing_key=%s",
                    agent_id,
                    exchange,
                    queue,
                    routing_key,
                )
                # Passos 1, 4 e 5 acontecem dentro do consumer:
                # 1. entrega cada mensagem ao handle_message acima;
                # 4. dá ACK quando handle_message termina sem erro;
                # 5. com erro, refila (requeue) se for recuperável
                #    e descarta se for InvalidMessageError.
                consumer.consume(
                    queue=queue,
                    callback=handle_message,
                    exchange=exchange,
                    routing_key=routing_key,
                    prefetch_count=prefetch_count,
                    # Mensagem malformada ou usuário já notificado via
                    # message.failed: descarta sem requeue. Os demais erros
                    # (ex.: Redis fora) voltam à fila para nova tentativa.
                    should_requeue=lambda exc: not isinstance(
                        exc, (InvalidMessageError, AgentProcessingError)
                    ),
                )
            except Exception:
                logger.exception(
                    "Falha no RabbitMQ; nova tentativa em %.1f segundo(s).",
                    reconnect_delay,
                )
                time.sleep(reconnect_delay)
            finally:
                connection.close()

    except KeyboardInterrupt:
        logger.info("Worker encerrado pelo usuário.")
    finally:
        agent_registry.stop()
        redis_connection.close()


if __name__ == "__main__":
    run_worker()