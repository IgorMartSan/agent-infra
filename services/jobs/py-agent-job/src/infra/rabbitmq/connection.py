import json
import logging
import os

import pika

from entity.message import AgentMessage, InvalidMessageError

logger = logging.getLogger(__name__)


class RabbitMQConnection:
    def __init__(self):
        self._connection = None
        self._channel = None
        self._delivery_tag = None

    def connect(self):
        if self._connection and self._connection.is_open:
            if self._channel and self._channel.is_open:
                return

            self._channel = self._connection.channel()
            self._channel.confirm_delivery()
            return

        credentials = pika.PlainCredentials(
            os.environ["RABBITMQ_USER"],
            os.environ["RABBITMQ_PASSWORD"],
        )
        parameters = pika.ConnectionParameters(
            host=os.environ["RABBITMQ_HOST"],
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            virtual_host="/",
            credentials=credentials,
            connection_attempts=3,
            retry_delay=1,
            socket_timeout=5,
            blocked_connection_timeout=5,
        )

        self._connection = pika.BlockingConnection(parameters)

        self._channel = self._connection.channel()
        self._channel.confirm_delivery()

    @property
    def channel(self):
        if not self._connection or self._connection.is_closed or not self._channel or self._channel.is_closed:
            self.connect()

        return self._channel

    def consume(self, queue):
        """Declara a fila e retorna as mensagens como AgentMessage."""
        channel = self.channel
        exchange = "agent.requests"
        channel.exchange_declare(exchange=exchange, exchange_type="direct", durable=True)
        channel.queue_declare(queue=queue, durable=True)
        channel.queue_bind(exchange=exchange, queue=queue, routing_key=queue.removesuffix(".requests"))
        channel.basic_qos(prefetch_count=1)
        return self._messages(channel, queue)

    def _messages(self, channel, queue):
        for method, _, body in channel.consume(queue=queue, auto_ack=False):
            try:
                message = AgentMessage.from_payload(json.loads(body))
            except (json.JSONDecodeError, UnicodeDecodeError, InvalidMessageError):
                logger.exception("Mensagem inválida descartada da fila.")
                channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                continue
            self._delivery_tag = method.delivery_tag
            yield message

    def ack(self):
        """Confirma a mensagem somente após a resposta ser publicada."""
        self.channel.basic_ack(delivery_tag=self._delivery_tag)
        self._delivery_tag = None

    def close(self):
        if self._connection and self._connection.is_open:
            self._connection.close()

        self._connection = None
        self._channel = None
        self._delivery_tag = None
