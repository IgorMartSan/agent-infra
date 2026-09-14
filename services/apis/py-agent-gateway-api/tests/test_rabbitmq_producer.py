import json

import pytest

from infra.rabbitmq.producer import RabbitMQProducer


class FakeChannel:
    def __init__(self, confirmed: bool = True):
        self.confirmed = confirmed
        self.declaration = None
        self.publication = None

    def exchange_declare(self, **kwargs) -> None:
        self.declaration = kwargs

    def basic_publish(self, **kwargs) -> bool:
        self.publication = kwargs
        return self.confirmed


class FakeConnection:
    def __init__(self, channel: FakeChannel):
        self.channel = channel


def test_publish_uses_durable_exchange_persistent_message_and_routing_key() -> None:
    channel = FakeChannel()
    producer = RabbitMQProducer(FakeConnection(channel))

    producer.publish(
        exchange='agent.requests',
        routing_key='agent.simple',
        message={'message_id': 'message-1'},
    )

    assert channel.declaration == {
        'exchange': 'agent.requests',
        'exchange_type': 'direct',
        'durable': True,
    }
    assert channel.publication['exchange'] == 'agent.requests'
    assert channel.publication['routing_key'] == 'agent.simple'
    assert channel.publication['mandatory'] is True
    assert json.loads(channel.publication['body']) == {'message_id': 'message-1'}
    assert channel.publication['properties'].content_type == 'application/json'
    assert channel.publication['properties'].delivery_mode == 2


def test_publish_fails_when_rabbitmq_does_not_confirm() -> None:
    producer = RabbitMQProducer(FakeConnection(FakeChannel(confirmed=False)))

    with pytest.raises(RuntimeError, match='não confirmou'):
        producer.publish(
            exchange='agent.requests',
            routing_key='agent.simple',
            message={'message_id': 'message-1'},
        )
