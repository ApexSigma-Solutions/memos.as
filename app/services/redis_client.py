import os
import json
import hashlib
import time
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta

import redis


class RedisClient:
    """
    Enhanced Redis client for memOS.as with comprehensive caching strategies.

    Implements:
    - Memory query result caching
    - Embedding vector caching
    - Frequent access pattern optimization
    - Cache invalidation strategies
    - Performance metrics tracking
    """

    def __init__(self):
        self.host = os.environ.get("REDIS_HOST", "localhost")
        self.port = int(os.environ.get("REDIS_PORT", 6379))
        self.password = os.environ.get("REDIS_PASSWORD", None)

        # Initialize Redis connection with error handling
        try:
            self.client = redis.Redis(
                host=self.host,
                port=self.port,
                password=self.password,
                db=0,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
            )
            # Test connection
            self.client.ping()
            print(f"✅ Connected to Redis at {self.host}:{self.port}")
        except Exception as e:
            print(f"❌ Failed to connect to Redis: {e}")
            self.client = None

    # Cache TTL Constants (in seconds)
    MEMORY_QUERY_TTL = 1800  # 30 minutes for query results
    EMBEDDING_TTL = 3600  # 1 hour for embeddings
    WORKING_MEMORY_TTL = 300  # 5 minutes for working memory
    TOOL_CACHE_TTL = 7200  # 2 hours for tool registry
    HEALTH_CHECK_TTL = 60  # 1 minute for health checks

    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Generate a consistent cache key from arguments."""
        key_data = f"{prefix}:" + ":".join(str(arg) for arg in args)
        return hashlib.md5(key_data.encode()).hexdigest()

    def is_connected(self) -> bool:
        """Check if Redis connection is available."""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except:
            return False

    # === Memory Query Caching ===

    def cache_query_result(
        self, query: str, results: List[Dict[str, Any]], top_k: int = 5
    ) -> bool:
        """Cache semantic search query results."""
        if not self.is_connected():
            return False

        try:
            cache_key = self._generate_cache_key("query", query, top_k)
            cache_data = {
                "results": results,
                "cached_at": datetime.utcnow().isoformat(),
                "query": query,
                "top_k": top_k,
                "result_count": len(results),
            }

            self.client.setex(
                cache_key, self.MEMORY_QUERY_TTL, json.dumps(cache_data)
            )

            # Track cache metrics
            self.client.incr("cache:queries:stored")
            return True
        except Exception as e:
            print(f"Error caching query result: {e}")
            return False

    def get_cached_query_result(
        self, query: str, top_k: int = 5
    ) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached query results."""
        if not self.is_connected():
            return None

        try:
            cache_key = self._generate_cache_key("query", query, top_k)
            cached_data = self.client.get(cache_key)

            if cached_data:
                cache_obj = json.loads(cached_data)
                self.client.incr("cache:queries:hits")
                return cache_obj["results"]
            else:
                self.client.incr("cache:queries:misses")
                return None
        except Exception as e:
            print(f"Error retrieving cached query: {e}")
            return None

    # === Embedding Vector Caching ===

    def cache_embedding(self, content: str, embedding: List[float]) -> bool:
        """Cache embedding vectors for content."""
        if not self.is_connected():
            return False

        try:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            cache_key = f"embedding:{content_hash}"

            embedding_data = {
                "embedding": embedding,
                "content_hash": content_hash,
                "cached_at": datetime.utcnow().isoformat(),
                "dimensions": len(embedding),
            }

            self.client.setex(
                cache_key, self.EMBEDDING_TTL, json.dumps(embedding_data)
            )

            self.client.incr("cache:embeddings:stored")
            return True
        except Exception as e:
            print(f"Error caching embedding: {e}")
            return False

    def get_cached_embedding(self, content: str) -> Optional[List[float]]:
        """Retrieve cached embedding for content."""
        if not self.is_connected():
            return None

        try:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            cache_key = f"embedding:{content_hash}"

            cached_data = self.client.get(cache_key)
            if cached_data:
                embedding_obj = json.loads(cached_data)
                self.client.incr("cache:embeddings:hits")
                return embedding_obj["embedding"]
            else:
                self.client.incr("cache:embeddings:misses")
                return None
        except Exception as e:
            print(f"Error retrieving cached embedding: {e}")
            return None

    # === Working Memory Caching (Tier 1) ===

    def store_working_memory(
        self, key: str, memory_data: Dict[str, Any]
    ) -> bool:
        """Store working memory with shorter TTL."""
        if not self.is_connected():
            return False

        try:
            cache_key = f"working_memory:{key}"
            memory_with_meta = {
                "data": memory_data,
                "stored_at": datetime.utcnow().isoformat(),
                "tier": "working",
            }

            self.client.setex(
                cache_key,
                self.WORKING_MEMORY_TTL,
                json.dumps(memory_with_meta),
            )

            self.client.incr("cache:working_memory:stored")
            return True
        except Exception as e:
            print(f"Error storing working memory: {e}")
            return False

    def get_working_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve working memory."""
        if not self.is_connected():
            return None

        try:
            cache_key = f"working_memory:{key}"
            cached_data = self.client.get(cache_key)

            if cached_data:
                memory_obj = json.loads(cached_data)
                self.client.incr("cache:working_memory:hits")
                return memory_obj["data"]
            else:
                self.client.incr("cache:working_memory:misses")
                return None
        except Exception as e:
            print(f"Error retrieving working memory: {e}")
            return None

    # === Tool Registry Caching ===

    def cache_tool_registry(self, tools: List[Dict[str, Any]]) -> bool:
        """Cache the complete tool registry."""
        if not self.is_connected():
            return False

        try:
            cache_data = {
                "tools": tools,
                "cached_at": datetime.utcnow().isoformat(),
                "tool_count": len(tools),
            }

            self.client.setex(
                "tool_registry:all",
                self.TOOL_CACHE_TTL,
                json.dumps(cache_data),
            )

            self.client.incr("cache:tools:stored")
            return True
        except Exception as e:
            print(f"Error caching tool registry: {e}")
            return False

    def get_cached_tool_registry(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached tool registry."""
        if not self.is_connected():
            return None

        try:
            cached_data = self.client.get("tool_registry:all")

            if cached_data:
                tool_obj = json.loads(cached_data)
                self.client.incr("cache:tools:hits")
                return tool_obj["tools"]
            else:
                self.client.incr("cache:tools:misses")
                return None
        except Exception as e:
            print(f"Error retrieving cached tools: {e}")
            return None

    # === Cache Invalidation Strategies ===

    def invalidate_memory_caches(
        self, memory_id: Optional[int] = None
    ) -> bool:
        """Invalidate memory-related caches when data changes."""
        if not self.is_connected():
            return False

        try:
            # Invalidate query result caches (they may now be stale)
            query_keys = self.client.keys("cache_key:query:*")
            if query_keys:
                self.client.delete(*query_keys)
                print(f"Invalidated {len(query_keys)} query cache entries")

            # If specific memory_id provided, invalidate related caches
            if memory_id:
                specific_keys = self.client.keys(f"*memory:{memory_id}*")
                if specific_keys:
                    self.client.delete(*specific_keys)
                    print(
                        f"Invalidated {len(specific_keys)} memory-specific cache entries"
                    )

            self.client.incr("cache:invalidations:memory")
            return True
        except Exception as e:
            print(f"Error invalidating memory caches: {e}")
            return False

    def invalidate_tool_caches(self) -> bool:
        """Invalidate tool registry caches when tools are updated."""
        if not self.is_connected():
            return False

        try:
            tool_keys = self.client.keys("tool_registry:*")
            if tool_keys:
                self.client.delete(*tool_keys)
                print(f"Invalidated {len(tool_keys)} tool cache entries")

            self.client.incr("cache:invalidations:tools")
            return True
        except Exception as e:
            print(f"Error invalidating tool caches: {e}")
            return False

    def clear_expired_caches(self) -> Dict[str, int]:
        """Manually clear expired cache entries and return stats."""
        if not self.is_connected():
            return {"error": "Redis not connected"}

        try:
            stats = {
                "queries_cleared": 0,
                "embeddings_cleared": 0,
                "working_memory_cleared": 0,
                "tools_cleared": 0,
            }

            # Check and clear expired entries by pattern
            patterns = [
                ("query:*", "queries_cleared"),
                ("embedding:*", "embeddings_cleared"),
                ("working_memory:*", "working_memory_cleared"),
                ("tool_registry:*", "tools_cleared"),
            ]

            for pattern, stat_key in patterns:
                keys = self.client.keys(pattern)
                expired_keys = []

                for key in keys:
                    ttl = self.client.ttl(key)
                    if ttl == -2:  # Key doesn't exist
                        expired_keys.append(key)

                if expired_keys:
                    self.client.delete(*expired_keys)
                    stats[stat_key] = len(expired_keys)

            return stats
        except Exception as e:
            print(f"Error clearing expired caches: {e}")
            return {"error": str(e)}

    # === Cache Performance Metrics ===

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache performance statistics."""
        if not self.is_connected():
            return {"error": "Redis not connected"}

        try:
            stats = {}

            # Cache hit/miss ratios
            metrics = [
                "cache:queries:hits",
                "cache:queries:misses",
                "cache:queries:stored",
                "cache:embeddings:hits",
                "cache:embeddings:misses",
                "cache:embeddings:stored",
                "cache:working_memory:hits",
                "cache:working_memory:misses",
                "cache:working_memory:stored",
                "cache:tools:hits",
                "cache:tools:misses",
                "cache:tools:stored",
                "cache:invalidations:memory",
                "cache:invalidations:tools",
            ]

            for metric in metrics:
                value = self.client.get(metric)
                stats[metric] = int(value) if value else 0

            # Calculate hit ratios
            def safe_ratio(hits: int, total: int) -> float:
                return round(hits / total * 100, 2) if total > 0 else 0.0

            stats["hit_ratios"] = {
                "queries": safe_ratio(
                    stats["cache:queries:hits"],
                    stats["cache:queries:hits"]
                    + stats["cache:queries:misses"],
                ),
                "embeddings": safe_ratio(
                    stats["cache:embeddings:hits"],
                    stats["cache:embeddings:hits"]
                    + stats["cache:embeddings:misses"],
                ),
                "working_memory": safe_ratio(
                    stats["cache:working_memory:hits"],
                    stats["cache:working_memory:hits"]
                    + stats["cache:working_memory:misses"],
                ),
                "tools": safe_ratio(
                    stats["cache:tools:hits"],
                    stats["cache:tools:hits"] + stats["cache:tools:misses"],
                ),
            }

            # Redis memory usage
            info = self.client.info("memory")
            stats["redis_memory"] = {
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "max_memory": info.get("maxmemory", 0),
            }

            return stats
        except Exception as e:
            print(f"Error getting cache stats: {e}")
            return {"error": str(e)}

    # === Legacy compatibility methods ===

    def set_cache(self, key: str, value: str, ttl: int = 3600):
        """Legacy method for basic cache operations."""
        if self.is_connected():
            self.client.setex(key, ttl, value)

    def get_cache(self, key: str) -> Optional[str]:
        """Legacy method for basic cache retrieval."""
        if not self.is_connected():
            return None
        value = self.client.get(key)
        return value if value else None

    def store_memory(self, key: str, memory_data: dict):
        """Legacy method - now uses working memory store."""
        self.store_working_memory(key, memory_data)

    def get_memory(self, key: str) -> Optional[dict]:
        """Legacy method - now uses working memory retrieval."""
        return self.get_working_memory(key)

    def clear_cache_pattern(self, pattern: str = "*") -> int:
        """Clear cache entries matching a pattern and return count."""
        if not self.is_connected():
            return 0

        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
                return len(keys)
            return 0
        except Exception as e:
            print(f"Error clearing cache pattern {pattern}: {e}")
            return 0


# Global Redis client instance
redis_client = RedisClient()


def get_redis_client() -> RedisClient:
    return redis_client
