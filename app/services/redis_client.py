import os
import json
import hashlib
import time
from typing import Any, Dict, List, Optional
from datetime import datetime
from app.config import get_config

import redis


from app.services.redis_utils import scan_iter

from prometheus_client import Counter

# Prometheus Metrics
try:
    APEX_MEMORY_EXPIRATION_RUNS_TOTAL = Counter(
        "apex_memory_expiration_runs_total",
        "Total number of memory expiration job runs",
    )
    APEX_MEMORIES_DELETED_TOTAL = Counter(
        "apex_memories_deleted_total", "Total number of expired memories deleted"
    )
    APEX_MEMORY_EXPIRATION_ERRORS_TOTAL = Counter(
        "apex_memory_expiration_errors_total",
        "Total number of errors during memory expiration",
    )
except ValueError:
    # Metrics already registered (e.g., in tests)
    from prometheus_client import REGISTRY

    APEX_MEMORY_EXPIRATION_RUNS_TOTAL = REGISTRY._names_to_collectors[
        "apex_memory_expiration_runs_total"
    ]
    APEX_MEMORIES_DELETED_TOTAL = REGISTRY._names_to_collectors[
        "apex_memories_deleted_total"
    ]
    APEX_MEMORY_EXPIRATION_ERRORS_TOTAL = REGISTRY._names_to_collectors[
        "apex_memory_expiration_errors_total"
    ]


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
        self.logger = get_config().get_logger(__name__)
        self.host = os.environ.get("REDIS_HOST", "localhost")
        self.port = int(os.environ.get("REDIS_PORT", 6379))
        self.password = os.environ.get("REDIS_PASSWORD", None)
        
        # Log connection parameters (without password)
        self.logger.info(f"Redis config - Host: {self.host}, Port: {self.port}, Password: {'SET' if self.password else 'NOT SET'}")

        # Initialize Redis connection with error handling
        self.client = None
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
            ping_result = self.client.ping()
            self.logger.info(f"Connected to Redis at {self.host}:{self.port} (ping: {ping_result})")
        except Exception as e:
            self.logger.error(f"Failed to connect to Redis: {e}")
            self.client = None

    # Cache TTLs are now driven from centralized config
    cfg = get_config()
    MEMORY_QUERY_TTL = cfg.get_ttl("MEMORY_QUERY_TTL")
    EMBEDDING_TTL = cfg.get_ttl("EMBEDDING_TTL")
    WORKING_MEMORY_TTL = cfg.get_ttl("WORKING_MEMORY_TTL")
    TOOL_CACHE_TTL = cfg.get_ttl("TOOL_CACHE_TTL")
    HEALTH_CHECK_TTL = cfg.get_ttl("HEALTH_CHECK_TTL")
    LLM_RESPONSE_TTL = cfg.get_ttl("LLM_RESPONSE_TTL")

    def _get_namespaced_key(self, key: str) -> str:
        """Prepend the APEX_NAMESPACE to the key."""
        return f"{self.cfg.get('APEX_NAMESPACE')}:{key}"

    def _generate_cache_key(self, prefix: str, *args) -> str:
        """Generate a consistent cache key from arguments."""
        key_data = f"{prefix}:" + ":".join(str(arg) for arg in args)
        return self._get_namespaced_key(hashlib.md5(key_data.encode()).hexdigest())

    def is_connected(self) -> bool:
        """Check if Redis connection is available."""
        if self.client is None:
            self.logger.warning("Redis client is None - not initialized")
            return False
        try:
            result = self.client.ping()
            return result
        except Exception as e:
            self.logger.error(f"Redis ping failed: {e}")
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

            self.client.setex(cache_key, self.MEMORY_QUERY_TTL, json.dumps(cache_data))

            # Track cache metrics
            self.client.incr("cache:queries:stored")
            return True
        except Exception as e:
            self.logger.error(f"Error caching query result: {e}")
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
            self.logger.error(f"Error retrieving cached query: {e}")
            return None

    # === Embedding Vector Caching ===

    def cache_embedding(self, content: str, embedding: List[float]) -> bool:
        """Cache embedding vectors for content."""
        if not self.is_connected():
            return False

        try:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            cache_key = self._get_namespaced_key(f"embedding:{content_hash}")

            embedding_data = {
                "embedding": embedding,
                "content_hash": content_hash,
                "cached_at": datetime.utcnow().isoformat(),
                "dimensions": len(embedding),
            }

            self.client.setex(cache_key, self.EMBEDDING_TTL, json.dumps(embedding_data))

            self.client.incr("cache:embeddings:stored")
            return True
        except Exception as e:
            self.logger.error(f"Error caching embedding: {e}")
            return False

    def get_cached_embedding(self, content: str) -> Optional[List[float]]:
        """Retrieve cached embedding for content."""
        if not self.is_connected():
            return None

        try:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            cache_key = self._get_namespaced_key(f"embedding:{content_hash}")

            cached_data = self.client.get(cache_key)
            if cached_data:
                embedding_obj = json.loads(cached_data)
                self.client.incr("cache:embeddings:hits")
                return embedding_obj["embedding"]
            else:
                self.client.incr("cache:embeddings:misses")
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving cached embedding: {e}")
            return None

    # === Working Memory Caching (Tier 1) ===

    def store_working_memory(
        self,
        key: str,
        memory_data: Dict[str, Any],
        expire_seconds: Optional[int] = None,
    ) -> bool:
        """Store working memory with shorter TTL."""
        if not self.is_connected():
            return False
        try:
            cache_key = self._get_namespaced_key(f"working_memory:{key}")
            memory_with_meta = {
                "data": memory_data,
                "stored_at": datetime.utcnow().isoformat(),
                "tier": "working",
            }

            ttl = (
                expire_seconds
                if expire_seconds is not None
                else self.WORKING_MEMORY_TTL
            )

            self.client.setex(cache_key, ttl, json.dumps(memory_with_meta))
            self.client.incr("cache:working_memory:stored")
            return True
        except Exception as e:
            self.logger.error(f"Error storing working memory: {e}")
            return False

    def get_working_memory(self, key: str) -> Optional[Dict[str, Any]]:
        """Retrieve working memory."""
        if not self.is_connected():
            return None

        try:
            cache_key = self._get_namespaced_key(f"working_memory:{key}")
            cached_data = self.client.get(cache_key)

            if cached_data:
                memory_obj = json.loads(cached_data)
                self.client.incr("cache:working_memory:hits")
                return memory_obj["data"]
            else:
                self.client.incr("cache:working_memory:misses")
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving working memory: {e}")
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
                self._get_namespaced_key("tool_registry:all"),
                self.TOOL_CACHE_TTL,
                json.dumps(cache_data),
            )

            self.client.incr("cache:tools:stored")
            return True
        except Exception as e:
            self.logger.error(f"Error caching tool registry: {e}")
            return False

    def get_cached_tool_registry(self) -> Optional[List[Dict[str, Any]]]:
        """Retrieve cached tool registry."""
        if not self.is_connected():
            return None

        try:
            cached_data = self.client.get(self._get_namespaced_key("tool_registry:all"))

            if cached_data:
                tool_obj = json.loads(cached_data)
                self.client.incr("cache:tools:hits")
                return tool_obj["tools"]
            else:
                self.client.incr("cache:tools:misses")
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving cached tools: {e}")
            return None

    # === Cache Invalidation Strategies ===

    def invalidate_memory_caches(self, memory_id: Optional[int] = None) -> bool:
        """Invalidate memory-related caches when data changes."""
        if not self.is_connected():
            return False

        try:
            # Invalidate query result caches (they may now be stale)
            query_keys = list(
                scan_iter(self.client, self._get_namespaced_key("query:*"))
            )
            if query_keys:
                self.client.delete(*query_keys)
                self.logger.info(f"Invalidated {len(query_keys)} query cache entries")

            # Invalidate embedding caches
            embedding_keys = list(
                scan_iter(self.client, self._get_namespaced_key("embedding:*"))
            )
            if embedding_keys:
                self.client.delete(*embedding_keys)
                self.logger.info(
                    f"Invalidated {len(embedding_keys)} embedding cache entries"
                )

            # Invalidate working memory caches
            working_memory_keys = list(
                scan_iter(self.client, self._get_namespaced_key("working_memory:*"))
            )
            if working_memory_keys:
                self.client.delete(*working_memory_keys)
                self.logger.info(
                    f"Invalidated {len(working_memory_keys)} working memory cache entries"
                )

            # If specific memory_id provided, invalidate related caches
            if memory_id:
                specific_keys = list(
                    scan_iter(
                        self.client, self._get_namespaced_key(f"*memory:{memory_id}*")
                    )
                )
                if specific_keys:
                    self.client.delete(*specific_keys)
                    self.logger.info(
                        f"Invalidated {len(specific_keys)} "
                        "memory-specific cache entries"
                    )

            self.client.incr("cache:invalidations:memory")
            return True
        except Exception as e:
            self.logger.error(f"Error invalidating memory caches: {e}")
            return False

    def invalidate_tool_caches(self) -> bool:
        """Invalidate tool registry caches when tools are updated."""
        if not self.is_connected():
            return False

        try:
            tool_keys = list(
                scan_iter(self.client, self._get_namespaced_key("tool_registry:*"))
            )
            if tool_keys:
                self.client.delete(*tool_keys)
                self.logger.info(f"Invalidated {len(tool_keys)} tool cache entries")

            self.client.incr("cache:invalidations:tools")
            return True
        except Exception as e:
            self.logger.error(f"Error invalidating tool caches: {e}")
            return False

    def clear_expired_caches(self) -> Dict[str, int]:
        """Manually clear expired cache entries and return stats."""
        if not self.is_connected():
            return {"error": "Redis not connected"}

        try:
            stats = {
                "no_ttl_keys": 0,
                "processed_patterns": 0,
            }

            # This utility scans for keys that DO NOT have an expiry (ttl == -1)
            # and returns counts. Redis auto-expires keys with TTLs; manual deletion
            # of expired keys is unnecessary. Use this to detect keys missing TTLs.
            patterns = [
                self._get_namespaced_key("query:*"),
                self._get_namespaced_key("embedding:*"),
                self._get_namespaced_key("working_memory:*"),
                self._get_namespaced_key("tool_registry:*"),
                self._get_namespaced_key("llm:*"),
            ]

            total_no_ttl = 0
            processed = 0

            for pattern in patterns:
                # Use scan to avoid blocking Redis in large datasets
                try:
                    for key in self.client.scan_iter(match=pattern):
                        processed += 1
                        try:
                            ttl = self.client.ttl(key)
                        except Exception:
                            ttl = None
                        if ttl == -1:
                            total_no_ttl += 1
                except Exception:
                    # If scan_iter fails for any reason, log and continue; do not use KEYS()
                    self.logger.warning("Failed to scan pattern %s; skipping", pattern)

            stats["no_ttl_keys"] = total_no_ttl
            stats["processed_patterns"] = processed

            return stats
        except Exception as e:
            self.logger.error(f"Error clearing expired caches: {e}")
            return {"error": str(e)}

    # === LLM Response Caching ===

    def cache_llm_response(
        self,
        model: str,
        prompt: str,
        response: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Cache LLM response for prompt and parameters."""
        if not self.is_connected():
            return False

        try:
            # Create cache key from prompt and parameters
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
            cache_key = self._get_namespaced_key(
                f"llm:{model}:{prompt_hash}:{temperature}:{max_tokens}"
            )

            cache_data = {
                "model": model,
                "prompt": prompt,
                "response": response,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "cached_at": datetime.utcnow().isoformat(),
                "metadata": metadata or {},
                "response_length": len(response),
                "prompt_length": len(prompt),
            }

            # Use config-driven TTL for LLM responses
            self.client.setex(cache_key, self.LLM_RESPONSE_TTL, json.dumps(cache_data))

            self.client.incr("cache:llm:stored")
            return True
        except Exception as e:
            self.logger.error(f"Error caching LLM response: {e}")
            return False

    def get_cached_llm_response(
        self, model: str, prompt: str, temperature: float = 0.7, max_tokens: int = 1000
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached LLM response."""
        if not self.is_connected():
            return None

        try:
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()
            cache_key = self._get_namespaced_key(
                f"llm:{model}:{prompt_hash}:{temperature}:{max_tokens}"
            )

            cached_data = self.client.get(cache_key)
            if cached_data:
                response_obj = json.loads(cached_data)
                self.client.incr("cache:llm:hits")
                return response_obj
            else:
                self.client.incr("cache:llm:misses")
                return None
        except Exception as e:
            self.logger.error(f"Error retrieving cached LLM response: {e}")
            return None

    # === LLM Token Usage Tracking ===

    def track_llm_usage(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int,
        request_id: Optional[str] = None,
    ) -> bool:
        """Track LLM token usage for cost monitoring."""
        if not self.is_connected():
            return False

        try:
            usage_data = {
                "model": model,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": request_id,
            }

            # Store individual usage record
            usage_key = self._get_namespaced_key(
                f"llm_usage:{model}:{int(time.time())}"
            )
            self.client.setex(usage_key, 2592000, json.dumps(usage_data))  # 30 days

            # Update aggregate counters
            self.client.incrby(
                self._get_namespaced_key(f"llm:total_tokens:{model}"), total_tokens
            )
            self.client.incrby(
                self._get_namespaced_key(f"llm:prompt_tokens:{model}"), prompt_tokens
            )
            self.client.incrby(
                self._get_namespaced_key(f"llm:completion_tokens:{model}"),
                completion_tokens,
            )
            self.client.incr(self._get_namespaced_key(f"llm:requests:{model}"))

            # Maintain a set of known models to avoid scanning keyspace for model names
            models_set = self._get_namespaced_key("llm:models")
            try:
                self.client.sadd(models_set, model)
            except Exception:
                # Non-fatal: continue even if set add fails
                self.logger.debug("Failed to add model to llm:models set: %s", model)

            return True
        except Exception as e:
            self.logger.error(f"Error tracking LLM usage: {e}")
            return False

    def get_llm_usage_stats(self, model: Optional[str] = None) -> Dict[str, Any]:
        """Get LLM usage statistics."""
        if not self.is_connected():
            return {"error": "Redis not connected"}

        try:
            stats = {}

            if model:
                models = [model]
            else:
                # Prefer explicit set of models to avoid scanning the keyspace
                models_set = self._get_namespaced_key("llm:models")
                try:
                    models = list(self.client.smembers(models_set) or [])
                except Exception:
                    models = []

                # Fallback to scan if no models were registered
                if not models:
                    usage_keys = list(
                        scan_iter(
                            self.client, self._get_namespaced_key("llm:requests:*")
                        )
                    )
                    models = [k.rsplit(":", 1)[-1] for k in usage_keys]

            for model_name in models:
                # Handle bytes from Redis
                if isinstance(model_name, bytes):
                    model_name = model_name.decode()
                stats[model_name] = {
                    "total_requests": int(
                        self.client.get(
                            self._get_namespaced_key(f"llm:requests:{model_name}")
                        )
                        or 0
                    ),
                    "total_tokens": int(
                        self.client.get(
                            self._get_namespaced_key(f"llm:total_tokens:{model_name}")
                        )
                        or 0
                    ),
                    "prompt_tokens": int(
                        self.client.get(
                            self._get_namespaced_key(f"llm:prompt_tokens:{model_name}")
                        )
                        or 0
                    ),
                    "completion_tokens": int(
                        self.client.get(
                            self._get_namespaced_key(
                                f"llm:completion_tokens:{model_name}"
                            )
                        )
                        or 0
                    ),
                }

            return stats
        except Exception as e:
            self.logger.error(f"Error getting LLM usage stats: {e}")
            return {"error": str(e)}

    # === LLM Model Performance Caching ===

    def cache_model_performance(
        self,
        model: str,
        operation: str,
        response_time: float,
        success: bool = True,
        error_message: Optional[str] = None,
    ) -> bool:
        """Cache model performance metrics."""
        if not self.is_connected():
            return False

        try:
            perf_data = {
                "model": model,
                "operation": operation,
                "response_time": response_time,
                "success": success,
                "error_message": error_message,
                "timestamp": datetime.utcnow().isoformat(),
            }

            # Store individual performance record
            perf_key = self._get_namespaced_key(
                f"llm_perf:{model}:{operation}:{int(time.time())}"
            )
            self.client.setex(perf_key, 604800, json.dumps(perf_data))  # 7 days

            # Update rolling averages (last 100 requests)
            success_key = self._get_namespaced_key(
                f"llm_perf_success:{model}:{operation}"
            )
            time_key = self._get_namespaced_key(f"llm_perf_time:{model}:{operation}")

            # Use Redis lists to maintain rolling windows
            self.client.lpush(success_key, 1 if success else 0)
            self.client.lpush(time_key, response_time)

            # Trim to last 100 entries
            self.client.ltrim(success_key, 0, 99)
            self.client.ltrim(time_key, 0, 99)

            return True
        except Exception as e:
            self.logger.error(f"Error caching model performance: {e}")
            return False

    def get_model_performance(self, model: str, operation: str) -> Dict[str, Any]:
        """Get model performance metrics."""
        if not self.is_connected():
            return {"error": "Redis not connected"}

        try:
            success_key = self._get_namespaced_key(
                f"llm_perf_success:{model}:{operation}"
            )
            time_key = self._get_namespaced_key(f"llm_perf_time:{model}:{operation}")

            success_scores = self.client.lrange(success_key, 0, -1)
            response_times = self.client.lrange(time_key, 0, -1)

            if not success_scores or not response_times:
                return {"error": "No performance data available"}

            # Calculate metrics
            success_rate = sum(int(s) for s in success_scores) / len(success_scores)
            avg_response_time = sum(float(t) for t in response_times) / len(
                response_times
            )
            min_response_time = min(float(t) for t in response_times)
            max_response_time = max(float(t) for t in response_times)

            return {
                "model": model,
                "operation": operation,
                "success_rate": round(success_rate * 100, 2),
                "avg_response_time": round(avg_response_time, 3),
                "min_response_time": round(min_response_time, 3),
                "max_response_time": round(max_response_time, 3),
                "sample_size": len(success_scores),
            }
        except Exception as e:
            self.logger.error(f"Error getting model performance: {e}")
            return {"error": str(e)}

    def get_cache_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache performance statistics."""
        if not self.is_connected():
            return {"error": "Redis not connected"}

        try:
            stats = {}

            # Cache hit/miss ratios - use namespaced keys
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
                namespaced_metric = self._get_namespaced_key(metric)
                value = self.client.get(namespaced_metric)
                stats[metric] = int(value) if value else 0

            # Calculate hit ratios
            def safe_ratio(hits: int, total: int) -> float:
                return round(hits / total * 100, 2) if total > 0 else 0.0

            stats["hit_ratios"] = {
                "queries": safe_ratio(
                    stats["cache:queries:hits"],
                    stats["cache:queries:hits"] + stats["cache:queries:misses"],
                ),
                "embeddings": safe_ratio(
                    stats["cache:embeddings:hits"],
                    stats["cache:embeddings:hits"] + stats["cache:embeddings:misses"],
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

            # Redis memory usage - handle fakeredis compatibility
            try:
                info = self.client.info("memory")
                stats["redis_memory"] = {
                    "used_memory": info.get("used_memory", 0),
                    "used_memory_human": info.get("used_memory_human", "0B"),
                    "max_memory": info.get("maxmemory", 0),
                }
            except Exception:
                # fakeredis doesn't support INFO command
                stats["redis_memory"] = {
                    "used_memory": 0,
                    "used_memory_human": "0B",
                    "max_memory": 0,
                    "note": "Memory info not available in test environment",
                }

            return stats
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
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
            keys = list(scan_iter(self.client, pattern))
            if keys:
                self.client.delete(*keys)
                return len(keys)
            return 0
        except Exception as e:
            self.logger.error(f"Error clearing cache pattern {pattern}: {e}")
            return 0


# Global Redis client instance
redis_client = RedisClient()


def get_redis_client() -> RedisClient:
    return redis_client
