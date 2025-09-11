import httpx

url = "http://localhost:8090/memory/store"
payload = {
    "content": "Current state of memOS.as: Core API endpoints (health, metrics, tool management, memory store, graph query) are implemented. Service clients for PostgreSQL, Qdrant, Redis, and Neo4j are integrated. Observability features (logging, metrics, tracing) are implemented, but Langfuse integration is currently disabled due to persistent import issues. Docker setup is configured for microservice architecture. Tests are failing due to connection issues when run from host, and import issues when run inside container.",
    "metadata": {
        "task": "Summarize memOS.as progress",
        "status": "IN_PROGRESS",
        "tags": ["progress", "summary", "memos.as"],
    },
}

try:
    response = httpx.post(url, json=payload)
    response.raise_for_status()
    print(response.json())
except httpx.RequestError as exc:
    print(f"An error occurred while requesting {exc.request.url!r}.")
    print(exc)
except httpx.HTTPStatusError as exc:
    print(
        f"Error response {exc.response.status_code} while requesting {exc.request.url!r}."
    )
    print(f"Response content: {exc.response.text}")
