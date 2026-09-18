# infrastructure/rabbitmq/consumer.py

import json

from infra.rabbitmq.connection import RabbitMQConnection


class RabbitMQConsumer:

    def __init__(self, connection: RabbitMQConnection):
        # Recebe a conexão pronta por injeção de dependência.
        self._connection = connection

    def consume(
        self,
        queue: str,
        callback,
    ) -> None:
        # Obtém o channel ativo da conexão.
        channel = self._connection.channel

        # Garante que a fila exista antes de tentar consumi-la.
        # durable=True mantém a definição da fila após restart do RabbitMQ.
        channel.queue_declare(
            queue=queue,
            durable=True,
        )

        # Limita a quantidade de mensagens não confirmadas por consumer.
        # prefetch_count=1 significa:
        # "só me entregue outra mensagem depois que eu confirmar a atual".
        channel.basic_qos(
            prefetch_count=1,
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
        callback,
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

        except Exception:
            # Informa que o processamento falhou.
            #
            # requeue=True faz a mensagem voltar para a fila
            # para poder ser processada novamente.
            channel.basic_nack(
                delivery_tag=method.delivery_tag,
                requeue=True,
            )

            raise
