import os
import pytest


def pytest_configure(config):
    """
    Register the "integration" pytest marker.
    
    Adds an ini-style marker description so tests can be marked as requiring integration infrastructure
    (e.g., Neo4j, PostgreSQL, Qdrant).
    
    Parameters:
        config: pytest.Config
            The pytest configuration object to which the marker description is added.
    """
    config.addinivalue_line("markers", "integration: mark test as requiring integration infra (neo4j, postgres, qdrant)")


@pytest.fixture(scope="session")
def neo4j_test_container(request):
    """
    Provide an optional pytest fixture that yields a Neo4j Bolt URL for tests or `None` if testcontainers is unavailable.
    
    Attempts to start a temporary Neo4j testcontainer and yields its Bolt URL so tests can connect to it. If the `testcontainers` package is not available or container startup fails, yields `None` so tests may use existing environment-configured infrastructure.
    
    Parameters:
        request: The pytest `request` fixture (used for fixture lifecycle management).
    
    Returns:
        bolt_url (str or None): The Bolt URL (e.g. "bolt://host:7687") of the started Neo4j container, or `None` if no container was started.
    
    Notes:
        - When a container is started, this fixture sets environment variables `NEO4J_URI` (to the Bolt URL) and `NEO4J_USERNAME` (to "neo4j") if they are not already set.
        - If the container provides a generated password, callers may read `NEO4J_PASSWORD` from the environment as needed.
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