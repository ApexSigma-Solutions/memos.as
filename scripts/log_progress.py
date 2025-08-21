import httpx

url = "http://localhost:8090/memory/store"
payload = {
    "content": "Created Pydantic model `GraphQueryRequest` in `app/models.py` for structured graph query requests.",
    "metadata": {
        "task": "Develop API Endpoints for Graph Queries - Schema",
        "status": "IN_PROGRESS",
        "tags": ["graph_api", "pydantic", "schema"]
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
