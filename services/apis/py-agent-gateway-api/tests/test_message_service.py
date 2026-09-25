import pytest

from service.message_service import routing_key_for


@pytest.mark.parametrize(
    'agent_id,routing_key',
    [
        ('simple-agent', 'agent.simple'),
        ('argus-agent', 'agent.argus'),
        ('customer-support-agent', 'agent.customer.support'),
    ],
)
def test_agent_routing(agent_id, routing_key):
    assert routing_key_for(agent_id) == routing_key
