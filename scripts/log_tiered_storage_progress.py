import httpx

url = "http://localhost:8090/memory/store"
payload = {
    "content": "Implemented and tested tiered storage endpoints (/memory/{tier}/store). All tests passed for Tier 1 (Redis), Tier 2 (PostgreSQL & Qdrant), and Tier 3 (Neo4j).",
    "metadata": {
        "task": "Implement and test tiered storage endpoints",
        "status": "DONE",
        "tags": ["api", "storage", "testing"],
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
