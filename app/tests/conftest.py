import os
import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "integration: mark test as requiring integration infra (neo4j, postgres, qdrant)")


@pytest.fixture(scope="session")
def neo4j_test_container(request):
    """
    Optional fixture: If python testcontainers is installed, spin up a Neo4j testcontainer
    for the duration of the test session and yield the bolt URL. If testcontainers is
    not available, yield None and tests can rely on environment variables or local compose.
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