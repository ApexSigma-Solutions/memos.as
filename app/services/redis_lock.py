import time
import uuid
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class RedisLock:
    """A small Redis-based lock with safe release and optional blocking acquire.

    This class uses a short Lua script to atomically verify owner before
    deleting the lock key. It provides a blocking `acquire` mode with a
    retry/backoff and a context-manager API for convenience.
    """

    def __init__(self, redis_client, key: str, ttl_ms: int = 60000):
        self.redis_client = redis_client
        self.key = key
        self.ttl_ms = int(ttl_ms)
        self.owner_id = str(uuid.uuid4())
        # Lua script: delete only if value matches expected owner id
        self.release_script = self.redis_client.register_script(
            """
            if redis.call("get", KEYS[1]) == ARGV[1] then
                return redis.call("del", KEYS[1])
            else
                return 0
            end
            """
        )

    def _get_current_owner(self) -> Optional[str]:
        v = self.redis_client.get(self.key)
        if v is None:
            return None
        # redis-py may return bytes
        if isinstance(v, bytes):
            try:
                return v.decode()
            except Exception:
                return str(v)
        return str(v)

    def acquire(
        self,
        blocking: bool = False,
        timeout_ms: Optional[int] = None,
        retry_delay_ms: int = 100,
    ) -> bool:
        """Attempt to acquire the lock.

        Args:
            blocking: If True, keep retrying until acquired or timeout.
            timeout_ms: Maximum time to wait when blocking (milliseconds). If None, block indefinitely.
            retry_delay_ms: Milliseconds between retries when blocking.

        Returns:
            True if the caller acquired the lock, False otherwise.
        """
        # fast path: non-blocking
        result = self.redis_client.set(self.key, self.owner_id, nx=True, px=self.ttl_ms)
        if result is not None and result is not False:
            return True

        if not blocking:
            return False

        # blocking path
        start = time.monotonic()
        timeout_s = None if timeout_ms is None else float(timeout_ms) / 1000.0
        retry_delay = float(retry_delay_ms) / 1000.0
        while True:
            result = self.redis_client.set(
                self.key, self.owner_id, nx=True, px=self.ttl_ms
            )
            if result is not None and result is not False:
                return True
            if timeout_s is not None and (time.monotonic() - start) >= timeout_s:
                return False
            time.sleep(retry_delay)

    def release(self) -> bool:
        """Release the lock atomically only if we own it.

        Returns True if the lock was released, False otherwise.
        """
        try:
            res = self.release_script(keys=[self.key], args=[self.owner_id])
            released = int(res) == 1
            if not released:
                logger.debug(
                    "RedisLock.release: lock not owned by caller or already released: %s",
                    self.key,
                )
            return released
        except Exception as e:
            # Fallback for environments that don't support Lua scripts (e.g., fakeredis)
            logger.debug("RedisLock.release: Lua script failed, using fallback: %s", e)
            try:
                current_owner = self._get_current_owner()
                if current_owner == self.owner_id:
                    return bool(self.redis_client.delete(self.key))
                else:
                    logger.debug(
                        "RedisLock.release: lock not owned by caller: %s", self.key
                    )
                    return False
            except Exception:
                logger.exception("RedisLock.release: error releasing lock %s", self.key)
                return False

    def renew(self) -> bool:
        """Renew the lock TTL only if we are still the owner.

        Returns True on success, False otherwise.
        """
        try:
            current = self._get_current_owner()
            if current == self.owner_id:
                return bool(self.redis_client.pexpire(self.key, self.ttl_ms))
            return False
        except Exception:
            logger.exception("RedisLock.renew: error renewing lock %s", self.key)
            return False

    # Context manager support
    def __enter__(self):
        acquired = self.acquire(blocking=True, timeout_ms=self.ttl_ms)
        if not acquired:
            raise TimeoutError(f"Failed to acquire redis lock: {self.key}")
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            self.release()
        except Exception:
            # release errors are non-fatal for context manager
            logger.exception("RedisLock.__exit__: failed to release %s", self.key)
