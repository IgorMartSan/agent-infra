import json
import sys
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from entity.message import AgentMessage
from infra.rabbitmq.connection import RabbitMQConnection


def ready_rabbitmq(channel):
    rabbitmq = RabbitMQConnection()
    rabbitmq._connection = Mock(is_open=True, is_closed=False)
    rabbitmq._channel = channel
    return rabbitmq


def test_consume_returns_agent_message_and_acknowledges_after_publish():
    channel = Mock(is_open=True, is_closed=False)
    body = json.dumps(
        {
            "application_id": "app",
            "chat_id": "chat",
            "message_id": "msg-1",
            "agent_id": "rsa-agent",
            "message": "Olá",
        }
    ).encode()
    channel.consume.return_value = iter([(Mock(delivery_tag=7), None, body)])
    rabbitmq = ready_rabbitmq(channel)

    messages = rabbitmq.consume("agent.rsa.requests")
    assert channel.queue_bind.call_args.kwargs == {
        "exchange": "agent.requests",
        "queue": "agent.rsa.requests",
        "routing_key": "agent.rsa",
    }
    assert next(messages) == AgentMessage("app", "msg-1", "rsa-agent", "Olá", chat_id="chat")
    channel.basic_ack.assert_not_called()

    rabbitmq.ack()
    channel.basic_ack.assert_called_once_with(delivery_tag=7)


def test_consume_discards_invalid_message_and_keeps_reading():
    channel = Mock(is_open=True, is_closed=False)
    valid = json.dumps(
        {
            "application_id": "app",
            "message_id": "msg-2",
            "agent_id": "simple-agent",
            "message": "Olá",
        }
    ).encode()
    channel.consume.return_value = iter(
        [
            (Mock(delivery_tag=8), None, b'{"message": "ok"}'),
            (Mock(delivery_tag=9), None, valid),
        ]
    )
    rabbitmq = ready_rabbitmq(channel)

    assert next(rabbitmq.consume("agent.simple.requests")).message_id == "msg-2"
    channel.basic_nack.assert_called_once_with(delivery_tag=8, requeue=False)
