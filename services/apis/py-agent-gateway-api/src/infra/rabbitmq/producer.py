import json

import pika

from infra.rabbitmq.connection import RabbitMQConnection


class RabbitMQProducer:

    def __init__(self, connection: RabbitMQConnection):
        self._connection = connection

    def publish(
        self,
        exchange: str,
        routing_key: str,
        message: dict,
    ) -> None:
        # Obtém o canal ativo da conexão com o RabbitMQ.
        # É através do channel que fazemos operações como declarar filas
        # e publicar mensagens.
        channel = self._connection.channel

        # Garante que o exchange exista antes da publicação.
        channel.exchange_declare(
            exchange=exchange,
            exchange_type='direct',
            durable=True,
        )

        # Publica efetivamente a mensagem no RabbitMQ.
        confirmed = channel.basic_publish(
            # O Gateway conhece apenas o exchange e a chave de roteamento.
            exchange=exchange,
            # O RabbitMQ seleciona as filas por meio dos bindings existentes.
            routing_key=routing_key,
            # Corpo da mensagem.
            # json.dumps transforma o dict Python em uma string JSON.
            body=json.dumps(message).encode('utf-8'),
            # Faz a publicação falhar se a mensagem não puder ser roteada.
            mandatory=True,
            # Define metadados/propriedades da mensagem.
            properties=pika.BasicProperties(
                # Informa ao consumidor que o conteúdo da mensagem é JSON.
                content_type='application/json',
                # Marca a mensagem como persistente.
                # delivery_mode=2 indica ao RabbitMQ que a mensagem
                # deve ser persistida em disco quando possível.
                delivery_mode=2,
            ),
        )

        if confirmed is False:
            raise RuntimeError('RabbitMQ não confirmou a publicação da mensagem.')
