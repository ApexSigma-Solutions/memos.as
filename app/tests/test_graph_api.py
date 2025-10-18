import httpx
import pytest
import os
from app.services.neo4j_client import Neo4jClient

API_HOST = os.environ.get("API_HOST", "localhost")
BASE_URL = f"http://{API_HOST}:8090"


@pytest.fixture(scope="module")
def neo4j_client():
    """
    Provide a module-scoped Neo4jClient instance for tests and ensure it is closed after the module completes.
    
    Returns:
        Neo4jClient: A client instance for use by tests in this module.
    """
    client = Neo4jClient()
    yield client
    client.close()


def test_graph_query_endpoint(neo4j_client):
    """
    Verifies that the /graph/query endpoint returns a created Concept node when queried by name.
    
    Creates a Concept node with a unique name, posts a query to /graph/query filtering by that name, asserts the response contains exactly one result whose node name matches the created concept, and deletes the created node afterward.
    """
    # Create a test concept node
    concept_name = "Test Graph Query Concept"
    neo4j_client.create_concept_node(concept_name)

    # Query for the created node
    url = f"{BASE_URL}/graph/query"
    payload = {
        "node_label": "Concept",
        "filters": {"name": concept_name}
    }

    try:
        with httpx.Client() as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            assert "result" in data
            assert len(data["result"]) == 1
            assert data["result"][0]["n"]["name"] == concept_name
    except httpx.RequestError as exc:
        pytest.fail(f"Request to {exc.request.url!r} failed: {exc}")
    except httpx.HTTPStatusError as exc:
        pytest.fail(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc.response.text}")
    finally:
        # Clean up the created node
        query = "MATCH (c:Concept {name: $name}) DELETE c"
        neo4j_client.run_cypher_query(query, {"name": concept_name})