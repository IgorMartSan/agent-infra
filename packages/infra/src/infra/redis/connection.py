# redis_connection.py
import logging

import redis.asyncio as redis
from redis.asyncio import Redis
from redis.exceptions import RedisError

logger = logging.getLogger(__name__)


class RedisConnection:
    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: str | None = None,
    ):
        self.client: Redis = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=False,
            socket_connect_timeout=3,
            socket_timeout=3,
            health_check_interval=30,
        )

    def get_client(self) -> Redis:
        return self.client

    async def ping(self) -> bool:
        try:
            await self.client.ping()
            return True
        except RedisError:
            logger.exception("Erro ao conectar no Redis")
            raise

    async def close(self) -> None:
        await self.client.aclose()