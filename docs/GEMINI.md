# Gemini Workspace Context: memOS.as

## Project Overview

`memos.as` is a Python-based FastAPI microservice that functions as the central memory and tool discovery hub for the DevEnviro AI agent ecosystem. It provides a unified API for agents to store experiences, discover capabilities, and ingest knowledge. The service is designed to be stateless, with all persistence managed by a shared, multi-tiered database infrastructure.

**Key Technologies:**

*   **Backend:** FastAPI, Python 3.11
*   **Database:**
    *   PostgreSQL: For structured data like tool registries and memory logs.
    *   Qdrant: For vector storage and semantic search of episodic memories.
    *   Redis: For high-speed, short-term working memory and caching.
*   **AI & Embeddings:**
    *   `google-generativeai`: For interacting with Google's generative AI models.
    *   The project is designed to work with local LLMs and embedding models run via LM Studio.
*   **Deployment:** Docker & Docker Compose

## Architecture

The system follows a decoupled microservice architecture. `memos.as` communicates with the `devenviro.as` Orchestrator and other services via a synchronous RESTful API. It also includes a knowledge ingestion service called "InGest-LLM" operated by a "Cortex Agent" to continuously build the knowledge base.

## Project Structure

The project is structured as a standard FastAPI application:

*   `app/`: Main application directory.
    *   `models.py`: Contains the Pydantic data models for API requests and responses.
    *   `services/`: Contains the client modules for interacting with external services (Redis, PostgreSQL, Qdrant).
    *   `main.py`: (To be created) The main FastAPI application file.
*   `context_portal/`: Contains the Alembic database migration scripts.
*   `.venv/`: The Python virtual environment.
*   `requirements.txt`: The list of Python dependencies.
*   `GEMINI.md`: This file, containing the project context.

## Building and Running

**1. Environment Setup:**

It is recommended to use `uv` for managing the virtual environment and dependencies.

```bash
# Create the virtual environment and install dependencies
uv venv && uv pip install -r requirements.txt

# Activate the virtual environment
# On Windows
.venv\Scripts\activate
# On macOS/Linux
source .venv/bin/activate
```

**2. Application Scaffolding:**

The initial application structure has been created with the following files:
*   `app/models.py`: Contains the Pydantic models for `StoreRequest`, `QueryRequest`, and `ToolRegistrationRequest`.
*   `app/services/redis_client.py`: (Empty) For Redis client implementation.
*   `app/services/postgres_client.py`: (Empty) For PostgreSQL client implementation.
*   `app/services/qdrant_client.py`: (Empty) For Qdrant client implementation.

**3. Running the Service:**

*TODO: Add instructions for running the FastAPI service. This will likely involve a `uvicorn` command, but the specific command is not yet defined in the project documentation.*

**4. Database Migrations:**

The project uses Alembic for database migrations. The database URL is set dynamically at runtime.

## Development Conventions

*   **Configuration:** Environment variables and configuration are managed through Pydantic's settings management.
*   **Database Schema:** The database schema is managed with Alembic migrations. The initial schema includes tables for `active_context`, `product_context`, `decisions`, `custom_data`, `system_patterns`, `progress_entries`, and `context_links`.
*   **Testing:** *TODO: Add information on testing practices once they are established.*

### Session Initialization Protocol (MANDATORY)
Every agent session must begin with:
1. **Check for existing context**: Look for `context.db` file in workspace
2. **Load existing context**: If found, retrieve and load project context
3. **Dynamic context retrieval**: Use RAG strategy with FTS and semantic search

### Core Protocol Rules
- **Retrieve First, Store Last**: Always check existing memory before storing new information
- **User Confirmation Required**: All write/update/delete operations need explicit user approval
- **Proactive Knowledge Management**: Identify and suggest logging decisions, progress, and relationships

### Memory System Integration

-  **Agent Memory Protocol**

- This project implements the Agent Memory Protocol - a set of best practices for AI agent interaction with the shared memory system.

### Society of Agents Collaboration
The system supports role-based collaboration:
- **@Claude**: Architect role
- **@Gemini**: Implementer role
- **Mandatory Agent Review (MAR)**: All artifacts require review and approval before integration

## Current State of Affairs (2025-08-17)

The `memOS.as` service is partially functional. The core API endpoints have been implemented, and the service can be started using `docker compose up`. However, there are significant issues with the test environment that are preventing the verification of the service's functionality.

### Key Achievements:
*   **Tiered Storage Endpoints:** The API endpoints for storing and retrieving memories from the different tiers (Redis, PostgreSQL, Qdrant, Neo4j) have been implemented.
*   **Tool Management Endpoints:** The API endpoints for registering, retrieving, and searching for tools have been implemented.
*   **Observability:** The service has been instrumented with basic observability using OpenTelemetry, Prometheus, and Jaeger.
*   **Dockerization:** The service has been containerized using Docker and Docker Compose.

### Current Challenges:
*   **Test Environment:** The tests are consistently failing with `httpx.ConnectError: [Errno 111] Connection refused` and `sqlalchemy.exc.OperationalError` when run from the `test-runner` container. This indicates a networking issue between the `test-runner` container and the other services.
*   **Host-based Testing:** Running the tests on the host machine is also failing with `ModuleNotFoundError` and `sqlalchemy.exc.OperationalError`, which indicates issues with resolving the service hostnames and the Python path.
*   **Neo4j Constraint Issue:** An issue with a Neo4j constraint violation was identified during end-to-end testing with `InGest-LLM.as`. A fix has been implemented, but it has not been possible to verify it due to the testing issues.

### Next Steps:
The immediate priority is to resolve the testing issues to be able to verify the functionality of the service. The following steps will be taken:
1.  **Stabilize the Test Environment:** A systematic approach will be taken to debug the `test-runner` service and resolve the networking and import issues.
2.  **Verify the Neo4j Fix:** Once the test environment is stable, the fix for the Neo4j constraint issue will be tested.
3.  **Full Integration Testing:** Once all the tests are passing, a full end-to-end integration test with `InGest-LLM.as` will be performed to verify the complete functionality of the `memOS.as` service.
