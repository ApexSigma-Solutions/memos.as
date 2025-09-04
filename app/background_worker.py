import time
import asyncio
from datetime import datetime
from tenacity import retry, stop_after_attempt, wait_exponential

from app.services.postgres_client import get_postgres_client, Memory
from app.services.qdrant_client import get_qdrant_client
from app.services.redis_client import get_redis_client
from app.services.redis_lock import RedisLock
from app.config import get_config

# Import Prometheus metrics
from prometheus_client import Counter, Histogram, Gauge

config = get_config()

# Prometheus Metrics for Memory Expiration
try:
    MEMORY_EXPIRATION_RUNS_TOTAL = Counter(
        "memory_expiration_runs_total", "Total number of memory expiration job runs"
    )
    MEMORY_EXPIRATION_ERRORS_TOTAL = Counter(
        "memory_expiration_errors_total", "Total number of errors during memory expiration"
    )
    MEMORIES_DELETED_TOTAL = Counter(
        "memories_deleted_total", "Total number of expired memories deleted"
    )
    EMBEDDINGS_DELETED_TOTAL = Counter(
        "embeddings_deleted_total", "Total number of embeddings deleted from Qdrant"
    )
    MEMORY_EXPIRATION_DURATION = Histogram(
        "memory_expiration_duration_seconds", "Time spent running memory expiration job"
    )
    MEMORY_EXPIRATION_LOCK_ACQUIRE_TIME = Histogram(
        "memory_expiration_lock_acquire_time_seconds", "Time spent acquiring expiration lock"
    )
    MEMORY_EXPIRATION_ACTIVE = Gauge(
        "memory_expiration_active", "Whether memory expiration job is currently running"
    )
except ValueError:
    # Metrics already registered (e.g., in tests)
    from prometheus_client import REGISTRY
    MEMORY_EXPIRATION_RUNS_TOTAL = REGISTRY._names_to_collectors["memory_expiration_runs_total"]
    MEMORY_EXPIRATION_ERRORS_TOTAL = REGISTRY._names_to_collectors["memory_expiration_errors_total"]
    MEMORIES_DELETED_TOTAL = REGISTRY._names_to_collectors["memories_deleted_total"]
    EMBEDDINGS_DELETED_TOTAL = REGISTRY._names_to_collectors["embeddings_deleted_total"]
    MEMORY_EXPIRATION_DURATION = REGISTRY._names_to_collectors["memory_expiration_duration_seconds"]
    MEMORY_EXPIRATION_LOCK_ACQUIRE_TIME = REGISTRY._names_to_collectors["memory_expiration_lock_acquire_time_seconds"]
    MEMORY_EXPIRATION_ACTIVE = REGISTRY._names_to_collectors["memory_expiration_active"]

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def delete_embedding_with_retry(qdrant_client, embedding_id):
    qdrant_client.delete_embedding(embedding_id)

def process_expired_memories_once():
    """Processes and deletes expired memories in a single run."""
    postgres_client = get_postgres_client()
    qdrant_client = get_qdrant_client()
    redis_client = get_redis_client()
    logger = config.get_logger(__name__)

    start_time = time.time()
    MEMORY_EXPIRATION_ACTIVE.set(1)
    MEMORY_EXPIRATION_RUNS_TOTAL.inc()

    lock_key = f"{config.get('APEX_NAMESPACE')}:memory_expiration_lock"
    lock = RedisLock(redis_client.client, lock_key, ttl_ms=300000)  # 5 minute TTL

    lock_start = time.time()
    acquired = lock.acquire(blocking=True, timeout_ms=10000)  # Wait up to 10 seconds for lock
    lock_duration = time.time() - lock_start
    MEMORY_EXPIRATION_LOCK_ACQUIRE_TIME.observe(lock_duration)

    if not acquired:
        logger.warning("Could not acquire lock for memory expiration after 10 seconds. Skipping run.")
        MEMORY_EXPIRATION_ACTIVE.set(0)
        return

    try:
        logger.info("Starting memory expiration job...")
        deleted_memories = 0
        deleted_embeddings = 0

        with postgres_client.get_session() as session:
            expired_memories = session.query(Memory).filter(
                Memory.expires_at <= datetime.utcnow()
            ).all()

            if expired_memories:
                logger.info(f"Found {len(expired_memories)} expired memories to process.")
                for memory in expired_memories:
                    try:
                        if memory.embedding_id:
                            delete_embedding_with_retry(qdrant_client, memory.embedding_id)
                            deleted_embeddings += 1
                            logger.debug(f"Deleted embedding {memory.embedding_id} for memory {memory.id}")

                        session.delete(memory)
                        deleted_memories += 1
                        logger.info(f"Deleted expired memory with ID: {memory.id}")
                    except Exception as e:
                        logger.error(f"Error deleting memory {memory.id}: {e}")
                        MEMORY_EXPIRATION_ERRORS_TOTAL.inc()
            else:
                logger.info("No expired memories found.")

        # Update metrics
        MEMORIES_DELETED_TOTAL.inc(deleted_memories)
        EMBEDDINGS_DELETED_TOTAL.inc(deleted_embeddings)

        duration = time.time() - start_time
        MEMORY_EXPIRATION_DURATION.observe(duration)

        logger.info(f"Memory expiration job completed. Deleted {deleted_memories} memories and {deleted_embeddings} embeddings in {duration:.2f}s")

    except Exception as e:
        logger.error(f"Critical error during memory expiration: {e}")
        MEMORY_EXPIRATION_ERRORS_TOTAL.inc()
        raise
    finally:
        try:
            lock.release()
        except Exception as e:
            logger.error(f"Error releasing expiration lock: {e}")
        MEMORY_EXPIRATION_ACTIVE.set(0)

async def run_expiration_loop():
    """Runs the memory expiration job in a loop with proper error handling."""
    logger = config.get_logger(__name__)
    interval_seconds = config.get('MEMORY_EXPIRATION_INTERVAL_SECONDS', 300)  # Default 5 minutes

    logger.info(f"Starting memory expiration loop with {interval_seconds}s interval")

    while True:
        try:
            process_expired_memories_once()
        except Exception as e:
            logger.error(f"Error in memory expiration loop: {e}")
            # Continue the loop even if one run fails
            MEMORY_EXPIRATION_ERRORS_TOTAL.inc()

        try:
            await asyncio.sleep(interval_seconds)
        except asyncio.CancelledError:
            logger.info("Memory expiration loop cancelled")
            break
        except Exception as e:
            logger.error(f"Error during sleep in expiration loop: {e}")
            # Sleep for a shorter time if there's an error
            await asyncio.sleep(60)

if __name__ == "__main__":
    asyncio.run(run_expiration_loop())
