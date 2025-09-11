import httpx

url = "http://localhost:8090/memory/store"
payload = {
    "content": "Troubleshooting persistent ImportError: 'trace_with_langfuse' not found. Attempting to resolve by adding __init__.py files to 'app' and 'app/services' directories to ensure proper package recognition.",
    "metadata": {
        "task": "Troubleshoot ModuleNotFoundError",
        "status": "IN_PROGRESS",
        "tags": ["troubleshooting", "python", "docker", "imports"],
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
