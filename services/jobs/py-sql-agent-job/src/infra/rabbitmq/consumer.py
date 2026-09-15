import json
import logging
from collections.abc import Callable
from typing import Any

from infra.rabbitmq.connection import RabbitMQConnection

logger = logging.getLogger(__name__)


class RabbitMQConsumer:
    def __init__(self, connection: RabbitMQConnection):
        # Recebe a conexão pronta por injeção de dependência.
        self._connection = connection

    def consume(
        self,
        queue: str,
        callback: Callable[[dict[str, Any]], None],
        exchange: str,
        routing_key: str,
        prefetch_count: int = 1,
        should_requeue: Callable[[Exception], bool] | None = None,
    ) -> None:
        # Obtém o channel ativo da conexão.
        channel = self._connection.channel

        # O worker declara o exchange que recebe as requisições dos agentes.
        channel.exchange_declare(
            exchange=exchange,
            exchange_type="direct",
            durable=True,
        )

        # Garante que a fila exista antes de tentar consumi-la.
        # durable=True mantém a definição da fila após restart do RabbitMQ.
        channel.queue_declare(
            queue=queue,
            durable=True,
        )

        # Associa somente a routing key deste agente à sua fila.
        channel.queue_bind(
            queue=queue,
            exchange=exchange,
            routing_key=routing_key,
        )

        # Limita a quantidade de mensagens não confirmadas por consumer.
        # prefetch_count=1 significa:
        # "só me entregue outra mensagem depois que eu confirmar a atual".
        channel.basic_qos(
            prefetch_count=prefetch_count,
        )

        # Registra a função que será executada quando uma mensagem chegar.
        channel.basic_consume(
            queue=queue,
            # Função chamada pelo RabbitMQ quando uma mensagem é entregue.
            on_message_callback=lambda ch, method, properties, body: self._handle_message(
                ch,
                method,
                properties,
                body,
                callback,
                should_requeue,
            ),
            # False significa que o RabbitMQ espera um ACK explícito.
            # A mensagem não é considerada concluída automaticamente.
            auto_ack=False,
        )

        # Mantém o processo bloqueado esperando novas mensagens.
        channel.start_consuming()

    def _handle_message(
        self,
        channel,
        method,
        properties,
        body,
        callback: Callable[[dict[str, Any]], None],
        should_requeue: Callable[[Exception], bool] | None,
    ) -> None:
        try:
            # Converte os bytes recebidos do RabbitMQ para JSON/dict Python.
            message = json.loads(body)

            # Executa a regra da aplicação.
            # No seu caso, provavelmente chamará o Orchestrator.
            callback(message)

            # Confirma para o RabbitMQ que a mensagem foi processada.
            # Após o ACK, o RabbitMQ pode removê-la da fila.
            channel.basic_ack(
                delivery_tag=method.delivery_tag,
            )

        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.exception("Mensagem descartada: o corpo não contém JSON válido.")
            channel.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=False,
            )
        except Exception as exc:
            # Informa que o processamento falhou.
            #
            # requeue=True faz a mensagem voltar para a fila
            # para poder ser processada novamente.
            requeue = should_requeue(exc) if should_requeue else True
            channel.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=requeue,
            )

            if requeue:
                raise

            logger.exception("Mensagem inválida descartada sem nova tentativa.")
