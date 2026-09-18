class MessageService:

    def __init__(self, producer, exchange: str = 'agent.requests'):
        self._producer = producer
        self._exchange = exchange

    def send(self, message: dict) -> None:
        agent_id = message['agent_id'].strip().lower()
        agent_name = agent_id.removesuffix('-agent')
        routing_key = f'agent.{agent_name.replace("-", ".")}'

        self._producer.publish(
            exchange=self._exchange,
            routing_key=routing_key,
            message=message,
        )
