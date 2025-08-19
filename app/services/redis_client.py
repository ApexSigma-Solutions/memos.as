import os
import json
import redis

from app.services.observability import get_observability


class RedisClient:
    def __init__(self):
        self.observability = get_observability()
        self.host = os.environ.get("REDIS_HOST", "devenviro_redis")
        self.port = int(os.environ.get("REDIS_PORT", 6379))
        self.client = redis.Redis(host=self.host, port=self.port, db=0)

    def set_cache(self, key: str, value: str, ttl: int = 3600):
        """
        Set a value in the Redis cache with a time-to-live (TTL).
        """
        try:
            self.client.setex(key, ttl, value)
            self.observability.record_cache_operation("redis_cache", hit=False)
        except Exception as e:
            self.observability.log_structured("error", "Error setting cache in Redis", error=str(e))

    def get_cache(self, key: str) -> str:
        """
        Get a value from the Redis cache.
        """
        try:
            value = self.client.get(key)
            if value:
                self.observability.record_cache_operation("redis_cache", hit=True)
                return value.decode("utf-8")
            else:
                self.observability.record_cache_operation("redis_cache", hit=False)
                return None
        except Exception as e:
            self.observability.log_structured("error", "Error getting cache from Redis", error=str(e))
            return None

    def store_memory(self, key: str, memory_data: dict):
        """
        Store a memory in Redis.
        """
        try:
            self.client.set(key, json.dumps(memory_data))
            self.observability.record_memory_operation("redis_store", "success", "tier1")
        except Exception as e:
            self.observability.record_memory_operation("redis_store", "failed", "tier1")
            self.observability.log_structured("error", "Error storing memory in Redis", error=str(e))

    def get_memory(self, key: str) -> dict:
        """
        Get a memory from Redis.
        """
        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            self.observability.log_structured("error", "Error getting memory from Redis", error=str(e))
            return None


# Global Redis client instance
redis_client = RedisClient()


def get_redis_client() -> RedisClient:
    return redis_client
