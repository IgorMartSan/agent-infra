from service.message_service import MessageService


class FakeProducer:
    def __init__(self) -> None:
        self.published: list[tuple[str, str, dict]] = []

    def publish(self, exchange: str, routing_key: str, message: dict) -> None:
        self.published.append((exchange, routing_key, message))


def test_publishes_to_exchange_using_routing_key_derived_from_agent_id() -> None:
    producer = FakeProducer()
    service = MessageService(producer, exchange='agent.requests')

    service.send({'agent_id': 'simple-agent', 'message': 'Olá'})

    assert producer.published == [
        (
            'agent.requests',
            'agent.simple',
            {'agent_id': 'simple-agent', 'message': 'Olá'},
        )
    ]
