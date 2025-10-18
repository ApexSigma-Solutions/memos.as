import httpx
import pytest
import random
import redis
import os
from app.services.redis_client import RedisClient
from app.services.neo4j_client import Neo4jClient

API_HOST = os.environ.get("API_HOST", "localhost")
BASE_URL = f"http://{API_HOST}:8090"

@pytest.fixture(scope="module")
def redis_client():
    """
    Fixture to initialize the Redis client for the test module.
    """
    client = RedisClient()
    return client

@pytest.fixture(scope="module")
def neo4j_client():
    """
    Provide a Neo4jClient instance for the test module and ensure it is closed after tests complete.
    
    Yields:
        Neo4jClient: an initialized Neo4j client for use in tests.
    """
    client = Neo4jClient()
    yield client
    client.close()

import httpx
import pytest
import random
import redis
import os
from app.services.redis_client import RedisClient
from app.services.neo4j_client import Neo4jClient

API_HOST = os.environ.get("API_HOST", "localhost")
BASE_URL = f"http://{API_HOST}:8090"


@pytest.fixture(scope="module")
def redis_client():
    """
    Provide a RedisClient instance for use in the test module.
    
    Returns:
        RedisClient: An initialized RedisClient for use by tests.
    """
    client = RedisClient()
    return client


@pytest.fixture(scope="module")
def neo4j_client():
    """
    Provide a Neo4jClient instance for the test module and ensure it is closed after tests complete.
    
    Yields:
        Neo4jClient: an initialized Neo4j client for use in tests.
    """
    client = Neo4jClient()
    yield client
    client.close()


def test_store_memory_tier1(redis_client):
    """
    Validate that POST /memory/1/store stores a memory in Redis and returns expected response fields.
    
    Sends a POST request to the Tier 1 memory store endpoint with sample content and metadata, asserts the response indicates success, contains tier==1 and a storage `key`, and verifies the stored Redis entry matches the submitted content. On HTTP request or response errors the test fails with a descriptive pytest failure.
    """
    url = f"{BASE_URL}/memory/1/store"
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
    url = f"{BASE_URL}/memory/2/store"
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
    Validate that POST /memory/3/store creates a Neo4j memory node and returns the stored node.
    
    Sends a POST request with content and metadata (including a randomized memory_id), asserts the response indicates success, has tier 3, and contains a node whose content matches the submitted content. After assertions, removes the created node from Neo4j to clean up.
    """
    url = f"{BASE_URL}/memory/3/store"
    content = "Test memory for Tier 3"
    # Generate a random memory_id to avoid conflicts
    payload = {
        "content": content,
        "metadata": {"source": "test", "memory_id": random.randint(1000, 9999)}
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