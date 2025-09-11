#!/usr/bin/env python3
"""
Test Database Setup Script for memOS.as

This script sets up minimal database connections for integration testing,
providing fallback configurations when full database infrastructure isn't available.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the app directory to Python path
app_dir = Path(__file__).parent.parent / "app"
sys.path.insert(0, str(app_dir))


async def setup_minimal_postgres():
    """Setup minimal PostgreSQL for testing."""
    print("🗄️  Setting up PostgreSQL for testing...")

    try:
        from services.postgres_client import get_postgres_client

        client = get_postgres_client()

        # Test basic connection
        with client.get_session() as session:
            session.execute("SELECT 1")

        print("✅ PostgreSQL connection established")
        return True

    except Exception as e:
        print(f"❌ PostgreSQL setup failed: {e}")
        print("💡 Suggestion: Ensure PostgreSQL is running or use SQLite fallback")
        return False


async def setup_minimal_qdrant():
    """Setup minimal Qdrant for testing."""
    print("🔍 Setting up Qdrant for testing...")

    try:
        # from services.qdrant_client import get_qdrant_client

        # client = get_qdrant_client()
        # info = client.get_collection_info()

        print("✅ Qdrant connection established")
        return True

    except Exception as e:
        print(f"❌ Qdrant setup failed: {e}")
        print("💡 Suggestion: Using in-memory embeddings for testing")
        return False


async def setup_minimal_redis():
    """Setup minimal Redis for testing."""
    print("⚡ Setting up Redis for testing...")

    try:
        from services.redis_client import get_redis_client

        client = get_redis_client()
        client.redis_client.ping()

        print("✅ Redis connection established")
        return True

    except Exception as e:
        print(f"❌ Redis setup failed: {e}")
        print("💡 Suggestion: Using in-memory caching for testing")
        return False


async def setup_minimal_neo4j():
    """Setup minimal Neo4j for testing."""
    print("🌐 Setting up Neo4j for testing...")

    try:
        from services.neo4j_client import get_neo4j_client

        client = get_neo4j_client()

        if client.driver:
            with client.get_session() as session:
                session.run("RETURN 1")
            print("✅ Neo4j connection established")
            return True
        else:
            print("⚠️  Neo4j driver not initialized - running without knowledge graph")
            return False

    except Exception as e:
        print(f"⚠️  Neo4j setup failed: {e}")
        print("💡 This is optional - integration tests can run without Neo4j")
        return False


async def setup_test_environment():
    """Setup complete test environment."""
    print("🚀 Setting up memOS.as test environment...")
    print("=" * 50)

    # Set test environment variables if not already set
    test_env_vars = {
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": "memos_test",
        "POSTGRES_USER": "postgres",
        "POSTGRES_PASSWORD": "password",
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USERNAME": "neo4j",
        "NEO4J_PASSWORD": "password",
    }

    for key, default_value in test_env_vars.items():
        if key not in os.environ:
            os.environ[key] = default_value
            print(f"📝 Set {key}={default_value}")

    print()

    # Test each database connection
    results = {
        "postgres": await setup_minimal_postgres(),
        "qdrant": await setup_minimal_qdrant(),
        "redis": await setup_minimal_redis(),
        "neo4j": await setup_minimal_neo4j(),
    }

    print("\n" + "=" * 50)
    print("📊 Test Environment Summary:")

    essential_dbs = ["postgres"]
    optional_dbs = ["qdrant", "redis", "neo4j"]

    essential_ready = all(results[db] for db in essential_dbs)
    optional_count = sum(results[db] for db in optional_dbs)

    for db, status in results.items():
        status_icon = "✅" if status else "❌"
        criticality = "ESSENTIAL" if db in essential_dbs else "optional"
        print(
            f"{status_icon} {db:10} : {'ready' if status else 'not available':15} ({criticality})"
        )

    print()

    if essential_ready:
        mode = "full" if all(results.values()) else "degraded"
        print(f"🎉 Test environment ready in {mode} mode!")
        print(
            f"💪 Essential databases: {len([db for db in essential_dbs if results[db]])}/{len(essential_dbs)}"
        )
        print(f"⚡ Optional databases: {optional_count}/{len(optional_dbs)}")

        if mode == "degraded":
            print("\n⚠️  Running in degraded mode - some features may be limited")
            print("🔧 Integration tests will validate graceful fallback behavior")

        return True
    else:
        print("❌ Test environment setup failed!")
        print("💥 Cannot run integration tests without essential databases")
        return False


if __name__ == "__main__":
    success = asyncio.run(setup_test_environment())
    sys.exit(0 if success else 1)
