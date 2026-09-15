import os

import pika
from dotenv import load_dotenv

load_dotenv()


class RabbitMQConnection:
    def __init__(self):
        self._connection = None
        self._channel = None

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
            port=int(os.environ["RABBITMQ_PORT"]),
            virtual_host=os.environ["RABBITMQ_VHOST"],
            credentials=credentials,
            connection_attempts=int(os.environ["RABBITMQ_CONNECTION_ATTEMPTS"]),
            retry_delay=float(os.environ["RABBITMQ_RETRY_DELAY"]),
            socket_timeout=float(os.environ["RABBITMQ_SOCKET_TIMEOUT"]),
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

    def close(self):
        if self._connection and self._connection.is_open:
            self._connection.close()

        self._connection = None
        self._channel = None


rabbitmq = RabbitMQConnection()
