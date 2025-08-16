import httpx
import pytest
import random
import redis
from app.services.redis_client import RedisClient
from app.services.neo4j_client import Neo4jClient

@pytest.fixture(scope="module")
def redis_client():
    """
    Fixture to initialize the Redis client for the test module.
    """
    client = RedisClient()
    client.host = "localhost"
    client.client = redis.Redis(host=client.host, port=client.port, db=0)
    return client

@pytest.fixture(scope="module")
def neo4j_client():
    """
    Fixture to initialize and close the Neo4j client for the test module.
    """
    client = Neo4jClient()
    yield client
    client.close()

def test_store_memory_tier1(redis_client):
    """
    Tests the POST /memory/1/store endpoint (Redis).
    """
    url = "http://localhost:8091/memory/1/store"
    content = "Test memory for Tier 1"
    payload = {
        "content": content,
        "metadata": {"source": "test"}
    }

    try:
        with httpx.Client() as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            assert data["success"] is True
            assert data["tier"] == 1
            assert "key" in data

            # Verify that the memory is stored in Redis
            stored_memory = redis_client.get_memory(data["key"])
            assert stored_memory is not None
            assert stored_memory["content"] == content

    except httpx.RequestError as exc:
        pytest.fail(f"Request to {exc.request.url!r} failed: {exc}")
    except httpx.HTTPStatusError as exc:
        pytest.fail(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc.response.text}")

def test_store_memory_tier2():
    """
    Tests the POST /memory/2/store endpoint (PostgreSQL & Qdrant).
    """
    url = "http://localhost:8091/memory/2/store"
    content = "Test memory for Tier 2"
    payload = {
        "content": content,
        "metadata": {"source": "test"}
    }

    try:
        with httpx.Client() as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            assert data["success"] is True
            assert "memory_id" in data
            assert "point_id" in data

    except httpx.RequestError as exc:
        pytest.fail(f"Request to {exc.request.url!r} failed: {exc}")
    except httpx.HTTPStatusError as exc:
        pytest.fail(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc.response.text}")

def test_store_memory_tier3(neo4j_client):
    """
    Tests the POST /memory/3/store endpoint (Neo4j).
    """
    url = "http://localhost:8091/memory/3/store"
    content = "Test memory for Tier 3"
    # Generate a random memory_id to avoid conflicts
    memory_id = random.randint(1000, 9999)
    payload = {
        "content": content,
        "metadata": {"source": "test", "memory_id": memory_id}
    }

    try:
        with httpx.Client() as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            assert data["success"] is True
            assert data["tier"] == 3
            assert "node" in data
            assert data["node"]["content"] == content

            # Clean up the created node
            node_id = data["node"]["id"]
            query = "MATCH (m:Memory {id: $id}) DETACH DELETE m"
            neo4j_client.run_cypher_query(query, {"id": node_id})

    except httpx.RequestError as exc:
        pytest.fail(f"Request to {exc.request.url!r} failed: {exc}")
    except httpx.HTTPStatusError as exc:
        pytest.fail(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc.response.text}")
