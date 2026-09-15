import json

import pika

from infra.rabbitmq.connection import RabbitMQConnection


class RabbitMQProducer:
    def __init__(self, connection: RabbitMQConnection):
        self._connection = connection

    def publish(
        self,
        queue: str,
        message: dict,
    ) -> None:
        # Obtém o canal ativo da conexão com o RabbitMQ.
        # É através do channel que fazemos operações como declarar filas
        # e publicar mensagens.
        channel = self._connection.channel

        # Garante que a fila exista.
        # Se ela ainda não existir, o RabbitMQ cria.
        # durable=True faz a fila sobreviver a reinicializações do RabbitMQ.
        channel.queue_declare(
            queue=queue,
            durable=True,
        )

        # Publica efetivamente a mensagem no RabbitMQ.
        confirmed = channel.basic_publish(
            # Exchange vazio significa que estamos usando o Default Exchange.
            # Nesse caso, o RabbitMQ usa a routing_key para encontrar
            # diretamente a fila de destino.
            exchange="",
            # Define para qual fila a mensagem será enviada.
            # Como estamos usando o Default Exchange,
            # a routing_key deve ter o mesmo nome da fila.
            routing_key=queue,
            # Corpo da mensagem.
            # json.dumps transforma o dict Python em uma string JSON.
            body=json.dumps(message).encode("utf-8"),
            # Faz a publicação falhar se a mensagem não puder ser roteada.
            mandatory=True,
            # Define metadados/propriedades da mensagem.
            properties=pika.BasicProperties(
                # Informa ao consumidor que o conteúdo da mensagem é JSON.
                content_type="application/json",
                # Marca a mensagem como persistente.
                # delivery_mode=2 indica ao RabbitMQ que a mensagem
                # deve ser persistida em disco quando possível.
                delivery_mode=2,
            ),
        )

        if confirmed is False:
            raise RuntimeError("RabbitMQ não confirmou a publicação da mensagem.")
