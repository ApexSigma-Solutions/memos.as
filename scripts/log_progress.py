import httpx

url = "http://localhost:8090/memory/store"
payload = {
    "content": "Added a test-runner service to docker-compose.yml for running integration tests within the Docker environment.",
    "metadata": {
        "task": "Implement robust integration testing",
        "status": "IN_PROGRESS",
        "tags": ["testing", "docker", "ci/cd"]
    }
}

try:
    response = httpx.post(url, json=payload)
    response.raise_for_status()
    print(response.json())
except httpx.RequestError as exc:
    print(f"An error occurred while requesting {exc.request.url!r}.")
    print(exc)
except httpx.HTTPStatusError as exc:
    print(f"Error response {exc.response.status_code} while requesting {exc.request.url!r}.")
    print(f"Response content: {exc.response.text}")
