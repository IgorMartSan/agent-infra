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
            os.getenv("RABBITMQ_USER") or "admin",
            os.getenv("RABBITMQ_PASSWORD") or "admin123",
        )
        parameters = pika.ConnectionParameters(
            host=os.getenv("RABBITMQ_HOST", "localhost"),
            port=int(os.getenv("RABBITMQ_PORT", "5672")),
            virtual_host=os.getenv("RABBITMQ_VHOST") or "/",
            credentials=credentials,
            connection_attempts=int(os.getenv("RABBITMQ_CONNECTION_ATTEMPTS", "1")),
            retry_delay=float(os.getenv("RABBITMQ_RETRY_DELAY", "1")),
            socket_timeout=float(os.getenv("RABBITMQ_SOCKET_TIMEOUT", "5")),
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
