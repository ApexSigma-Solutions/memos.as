import os
import json
import redis


class RedisClient:
    def __init__(self):
        self.host = os.environ.get("REDIS_HOST", "devenviro_redis")
        self.port = int(os.environ.get("REDIS_PORT", 6379))
        self.client = redis.Redis(host=self.host, port=self.port, db=0)

    def set_cache(self, key: str, value: str, ttl: int = 3600):
        """
        Set a value in the Redis cache with a time-to-live (TTL).
        """
        self.client.setex(key, ttl, value)

    def get_cache(self, key: str) -> str:
        """
        Get a value from the Redis cache.
        """
        value = self.client.get(key)
        return value.decode("utf-8") if value else None

    def store_memory(self, key: str, memory_data: dict):
        """
        Store a memory in Redis.
        """
        self.client.set(key, json.dumps(memory_data))

    def get_memory(self, key: str) -> dict:
        """
        Get a memory from Redis.
        """
        value = self.client.get(key)
        return json.loads(value) if value else None


# Global Redis client instance
redis_client = RedisClient()


def get_redis_client() -> RedisClient:
    return redis_client
