import httpx
import pytest
from app.services.neo4j_client import Neo4jClient

@pytest.fixture(scope="module")
def neo4j_client():
    """
    Fixture to initialize and close the Neo4j client for the test module.
    """
    client = Neo4jClient()
    yield client
    client.close()

def test_graph_query_endpoint(neo4j_client):
    """
    Tests the /graph/query endpoint.
    """
    # Create a test concept node
    concept_name = "Test Graph Query Concept"
    neo4j_client.create_concept_node(concept_name)

    # Query for the created node
    url = "http://localhost:8091/graph/query"
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
