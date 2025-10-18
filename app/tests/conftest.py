import os
import pytest


def pytest_configure(config):
    """
    Register the "integration" pytest marker for tests that require external integration infrastructure.
    
    Parameters:
        config (pytest.Config): Pytest configuration object used to register markers.
    """
    config.addinivalue_line("markers", "integration: mark test as requiring integration infra (neo4j, postgres, qdrant)")


@pytest.fixture(scope="session")
def neo4j_test_container(request):
    """
    Provide a session-scoped pytest fixture that yields a Neo4j Bolt URL when a Neo4j testcontainer can be started, or yields None if testcontainers is not available.
    
    If a container is started, sets NEO4J_URI and NEO4J_USERNAME in the environment only if they are not already set. If the container generates a password, callers may read NEO4J_PASSWORD from the environment.
    
    Returns:
        bolt_url (str): The Bolt URI for the started Neo4j container (e.g. "bolt://host:port"), or `None` if testcontainers is unavailable.
    """
    try:
        from testcontainers.neo4j import Neo4jContainer
    except Exception:
        # testcontainers not installed - return None so tests can use existing infra
        yield None
        return

    # start a neo4j container for tests
    with Neo4jContainer("neo4j:5.15-community") as neo:
        bolt_url = f"bolt://{neo.get_container_host_ip()}:{neo.get_exposed_port(7687)}"
        os.environ.setdefault("NEO4J_URI", bolt_url)
        os.environ.setdefault("NEO4J_USERNAME", "neo4j")
        # If the container sets a generated password, callers should read NEO4J_PASSWORD as needed
        yield bolt_url