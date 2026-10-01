class QueueOverloaded(Exception):
    """A fila atingiu o limite de mensagens."""


class QueueThreshold:
    def __init__(self, message_count, max_messages=100):
        self._message_count = message_count
        self._max_messages = max_messages

    def check(self, queue_name):
        if self._message_count(queue_name) >= self._max_messages:
            raise QueueOverloaded("A fila de processamento está cheia no momento. Tente novamente em alguns instantes.")
