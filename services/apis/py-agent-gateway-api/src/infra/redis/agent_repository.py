"""Consulta os heartbeats publicados pelos workers."""


class AgentRepository:
    def __init__(self, redis_client, prefix='agent:online:'):
        self._redis = redis_client
        self._prefix = prefix

    def is_available(self, agent_id):
        return bool(self._redis.exists(f'{self._prefix}{agent_id}'))

    def list_available(self):
        keys = self._redis.scan_iter(match=f'{self._prefix}*', count=100)
        ids = {(key.decode() if isinstance(key, bytes) else key).removeprefix(self._prefix) for key in keys}
        return [{'agent_id': agent_id} for agent_id in sorted(ids)]
