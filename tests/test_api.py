import httpx
import pytest
import os

API_HOST = os.environ.get("API_HOST", "localhost")
BASE_URL = f"http://{API_HOST}:8090"

@pytest.mark.parametrize("execution_number", range(10))
def test_health_check_multiple_times(execution_number):
    """
    Tests the /health endpoint to ensure the service is running and responsive.
    Runs multiple times to check for connection persistence.
    """
    url = f"{BASE_URL}/health"
    try:
        with httpx.Client() as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
            assert data["status"] == "healthy"
            assert data["services"]["postgres"] == "connected"
            assert data["services"]["qdrant"] == "connected"
            assert data["services"]["redis"] == "connected"
    except httpx.RequestError as exc:
        pytest.fail(f"Request to {exc.request.url!r} failed: {exc}")
    except httpx.HTTPStatusError as exc:
        pytest.fail(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}: {exc.response.text}")
