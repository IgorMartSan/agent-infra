import os

from redis import Redis


class RedisConnection:
    def __init__(self) -> None:
        self._client = Redis(
            host=os.environ["REDIS_HOST"],
            port=int(os.environ["REDIS_PORT"]),
            db=int(os.environ["REDIS_DB"]),
            password=os.environ["REDIS_PASSWORD"] or None,
            decode_responses=False,
            socket_connect_timeout=3,
            socket_timeout=3,
            health_check_interval=30,
        )

    def get_client(self) -> Redis:
        return self._client

    def close(self) -> None:
        self._client.close()
