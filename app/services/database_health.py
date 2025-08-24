"""
Database Health Check and Graceful Fallback Service

This service provides comprehensive database health monitoring and graceful
fallbacks to ensure memOS.as can operate even when some databases are unavailable.
"""

import os
import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

class DatabaseHealthManager:
    """Manages database health checks and provides fallback mechanisms."""

    def __init__(self):
        self.health_status = {
            "postgres": {"status": "unknown", "error": None},
            "qdrant": {"status": "unknown", "error": None},
            "redis": {"status": "unknown", "error": None},
            "neo4j": {"status": "unknown", "error": None}
        }

    def check_postgres_health(self) -> Dict[str, Any]:
        """Check PostgreSQL connection health."""
        try:
            from .postgres_client import get_postgres_client
            client = get_postgres_client()

            # Try a simple query
            with client.get_session() as session:
                session.execute("SELECT 1")

            self.health_status["postgres"] = {"status": "healthy", "error": None}
            logger.info("PostgreSQL connection healthy")

        except Exception as e:
            self.health_status["postgres"] = {"status": "unhealthy", "error": str(e)}
            logger.warning(f"PostgreSQL connection failed: {e}")

        return self.health_status["postgres"]

    def check_qdrant_health(self) -> Dict[str, Any]:
        """Check Qdrant connection health."""
        try:
            from .qdrant_client import get_qdrant_client
            client = get_qdrant_client()

            # Try to get collection info
            info = client.get_collection_info()

            self.health_status["qdrant"] = {"status": "healthy", "error": None}
            logger.info("Qdrant connection healthy")

        except Exception as e:
            self.health_status["qdrant"] = {"status": "unhealthy", "error": str(e)}
            logger.warning(f"Qdrant connection failed: {e}")

        return self.health_status["qdrant"]

    def check_redis_health(self) -> Dict[str, Any]:
        """Check Redis connection health."""
        try:
            from .redis_client import get_redis_client
            client = get_redis_client()

            # Try a simple ping
            client.client.ping()

            self.health_status["redis"] = {"status": "healthy", "error": None}
            logger.info("Redis connection healthy")

        except Exception as e:
            self.health_status["redis"] = {"status": "unhealthy", "error": str(e)}
            logger.warning(f"Redis connection failed: {e}")

        return self.health_status["redis"]

    def check_neo4j_health(self) -> Dict[str, Any]:
        """Check Neo4j connection health."""
        try:
            from .neo4j_client import get_neo4j_client
            client = get_neo4j_client()

            if client.driver is None:
                raise Exception("Neo4j driver not initialized - check connection settings")

            # Try a simple query
            with client.get_session() as session:
                session.run("RETURN 1")

            self.health_status["neo4j"] = {"status": "healthy", "error": None}
            logger.info("Neo4j connection healthy")

        except Exception as e:
            self.health_status["neo4j"] = {"status": "unhealthy", "error": str(e)}
            logger.warning(f"Neo4j connection failed: {e}")

        return self.health_status["neo4j"]

    def check_all_databases(self) -> Dict[str, Dict[str, Any]]:
        """Check health of all databases."""
        self.check_postgres_health()
        self.check_qdrant_health()
        self.check_redis_health()
        self.check_neo4j_health()

        return self.health_status.copy()

    def get_operational_databases(self) -> Dict[str, bool]:
        """Get list of databases that are operational."""
        return {
            db: status["status"] == "healthy"
            for db, status in self.health_status.items()
        }

    def can_store_memory(self) -> bool:
        """Check if memory storage is possible with current database status."""
        # At minimum, we need PostgreSQL for memory storage
        return self.health_status["postgres"]["status"] == "healthy"

    def get_storage_strategy(self) -> Dict[str, Any]:
        """Determine the best storage strategy based on database availability."""
        operational = self.get_operational_databases()

        strategy = {
            "can_store": operational["postgres"],
            "use_embeddings": operational["postgres"] and operational["qdrant"],
            "use_caching": operational["redis"],
            "use_knowledge_graph": operational["neo4j"],
            "degraded_mode": not all(operational.values())
        }

        return strategy

# Global health manager instance
health_manager = DatabaseHealthManager()

def get_health_manager() -> DatabaseHealthManager:
    """Get the global health manager instance."""
    return health_manager
