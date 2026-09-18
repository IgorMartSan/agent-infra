class QueueOverloaded(Exception):
    """Indica que a fila do agente atingiu o limite de mensagens."""


class QueueThreshold:
    """Bloqueia a publicação quando a fila do agente atinge o limite.

    A profundidade é obtida com uma declaração passiva da fila
    (queue_declare passive): o RabbitMQ devolve a contagem atual
    sem criar nem alterar a fila.
    """

    def __init__(self, channel_getter, max_messages: int = 100) -> None:
        self._channel_getter = channel_getter
        self._max_messages = max_messages

    def check(self, queue_name: str) -> None:
        method = self._channel_getter().queue_declare(
            queue=queue_name,
            passive=True,
            durable=True,
        )
        message_count = method.method.message_count

        if message_count >= self._max_messages:
            raise QueueOverloaded(
                'A fila de processamento está cheia no momento. '
                'Tente novamente em alguns instantes.'
            )