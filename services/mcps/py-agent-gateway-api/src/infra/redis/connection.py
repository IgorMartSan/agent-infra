import os

from redis import Redis


class RedisConnection:
    def __init__(self) -> None:
        self._client = Redis(
            host=os.getenv('REDIS_HOST', 'redis'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            password=os.getenv('REDIS_PASSWORD') or None,
            decode_responses=True,
            socket_connect_timeout=3,
            socket_timeout=3,
        )

    def get_client(self) -> Redis:
        return self._client

    def close(self) -> None:
        self._client.close()
