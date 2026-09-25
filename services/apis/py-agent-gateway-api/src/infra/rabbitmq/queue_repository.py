"""Leitura da profundidade da fila sem criar filas."""


class QueueRepository:
    def __init__(self, connection):
        self._connection = connection

    def message_count(self, queue_name):
        result = self._connection.channel.queue_declare(queue=queue_name, passive=True, durable=True)
        return result.method.message_count
