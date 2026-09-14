from types import SimpleNamespace

import pytest

from infra.rabbitmq.consumer import RabbitMQConsumer


class FakeChannel:
    def __init__(self) -> None:
        self.acked: list[int] = []
        self.nacked: list[tuple[int, bool]] = []
        self.exchange_declaration = None
        self.queue_declaration = None
        self.binding = None
        self.qos = None
        self.consumer = None
        self.consuming = False

    def exchange_declare(self, **kwargs) -> None:
        self.exchange_declaration = kwargs

    def queue_declare(self, **kwargs) -> None:
        self.queue_declaration = kwargs

    def queue_bind(self, **kwargs) -> None:
        self.binding = kwargs

    def basic_qos(self, **kwargs) -> None:
        self.qos = kwargs

    def basic_consume(self, **kwargs) -> None:
        self.consumer = kwargs

    def start_consuming(self) -> None:
        self.consuming = True

    def basic_ack(self, delivery_tag: int) -> None:
        self.acked.append(delivery_tag)

    def basic_nack(self, delivery_tag: int, requeue: bool) -> None:
        self.nacked.append((delivery_tag, requeue))


def deliver(body: bytes, callback, should_requeue=None) -> FakeChannel:
    channel = FakeChannel()
    consumer = RabbitMQConsumer(connection=SimpleNamespace())
    consumer._handle_message(
        channel,
        SimpleNamespace(delivery_tag=7),
        None,
        body,
        callback,
        should_requeue,
    )
    return channel


def test_declares_exchange_queue_and_agent_binding_before_consuming() -> None:
    channel = FakeChannel()
    consumer = RabbitMQConsumer(connection=SimpleNamespace(channel=channel))

    consumer.consume(
        queue="agent.simple.requests",
        callback=lambda _message: None,
        exchange="agent.requests",
        routing_key="agent.simple",
    )

    assert channel.exchange_declaration == {
        "exchange": "agent.requests",
        "exchange_type": "direct",
        "durable": True,
    }
    assert channel.queue_declaration == {
        "queue": "agent.simple.requests",
        "durable": True,
    }
    assert channel.binding == {
        "queue": "agent.simple.requests",
        "exchange": "agent.requests",
        "routing_key": "agent.simple",
    }
    assert channel.consuming is True


def test_acknowledges_only_after_successful_processing() -> None:
    received: list[dict] = []

    channel = deliver(b'{"message": "ola"}', received.append)

    assert received == [{"message": "ola"}]
    assert channel.acked == [7]
    assert channel.nacked == []


def test_discards_invalid_json() -> None:
    channel = deliver(b"not-json", lambda _message: None)

    assert channel.acked == []
    assert channel.nacked == [(7, False)]


def test_requeues_transient_processing_error() -> None:
    error = RuntimeError("temporary")

    with pytest.raises(RuntimeError, match="temporary"):
        deliver(b'{"message": "ola"}', lambda _message: (_ for _ in ()).throw(error))


def test_discards_non_retryable_processing_error() -> None:
    error = ValueError("invalid")
    channel = deliver(
        b'{"message": ""}',
        lambda _message: (_ for _ in ()).throw(error),
        should_requeue=lambda exc: not isinstance(exc, ValueError),
    )

    assert channel.acked == []
    assert channel.nacked == [(7, False)]
