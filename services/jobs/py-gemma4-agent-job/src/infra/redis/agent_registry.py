import logging
import threading

logger = logging.getLogger(__name__)


class AgentRegistry:
    def __init__(self, redis_client, agent_id: str, ttl_seconds: int = 30, interval_seconds: float = 10.0) -> None:
        self._redis = redis_client
        self._key = f"agent:online:{agent_id}"
        self._ttl = ttl_seconds
        self._interval = interval_seconds
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self._redis.set(self._key, "1", ex=self._ttl)
        self._thread = threading.Thread(target=self._renew, daemon=True)
        self._thread.start()

    def _renew(self) -> None:
        while not self._stop_event.wait(self._interval):
            try:
                self._redis.set(self._key, "1", ex=self._ttl)
            except Exception:
                logger.exception("Falha ao renovar heartbeat %s", self._key)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=self._interval)
        try:
            self._redis.delete(self._key)
        except Exception:
            logger.exception("Falha ao remover heartbeat %s", self._key)
