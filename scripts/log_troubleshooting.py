import httpx

url = "http://localhost:8090/memory/store"
payload = {
    "content": "Troubleshooting session for memOS.as service startup. Faced persistent httpx.ConnectError and ModuleNotFoundError. Resolved by correcting the Dockerfile (WORKDIR, COPY, PYTHONPATH), fixing import paths in app/main.py, updating .env with correct service hostnames, and adding missing dependencies to requirements.txt. The final workaround for logging progress was to execute the script inside the container.",
    "metadata": {
        "task": "Troubleshoot memOS.as service startup",
        "status": "DONE",
        "tags": ["troubleshooting", "docker", "python", "fastapi"],
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
