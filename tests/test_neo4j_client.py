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

def test_neo4j_connection(neo4j_client):
    """
    Test the connection to the Neo4j database.
    """
    assert neo4j_client.driver is not None

def test_create_and_get_concept_node(neo4j_client):
    """
    Test creating and retrieving a concept node.
    """
    # Create a test concept node
    concept_name = "Test Concept"
    created_node = neo4j_client.create_concept_node(concept_name)
    assert created_node is not None
    assert created_node["name"] == concept_name

    # Get the node by its name
    query = "MATCH (c:Concept {name: $name}) RETURN c"

    result = neo4j_client.run_cypher_query(query, {"name": concept_name})
    assert len(result) == 1
    retrieved_node = result[0]["c"]
    assert retrieved_node["name"] == concept_name

    # Clean up the created node
    query = "MATCH (c:Concept {name: $name}) DELETE c"
    neo4j_client.run_cypher_query(query, {"name": concept_name})

def test_create_relationship(neo4j_client):
    """
    Test creating a relationship between two concept nodes.
    """
    # Create two test concept nodes
    concept1_name = "Test Concept 1"
    concept2_name = "Test Concept 2"
    neo4j_client.create_concept_node(concept1_name)
    neo4j_client.create_concept_node(concept2_name)

    # Create a relationship between them
    query = """
    MATCH (a:Concept {name: $name1}), (b:Concept {name: $name2})
    CREATE (a)-[r:RELATED_TO]->(b)
    RETURN r
    """
    result = neo4j_client.run_cypher_query(query, {"name1": concept1_name, "name2": concept2_name})
    assert len(result) == 1

    # Clean up the created nodes and relationship
    query = "MATCH (c:Concept) WHERE c.name STARTS WITH 'Test Concept' DETACH DELETE c"
    neo4j_client.run_cypher_query(query)
