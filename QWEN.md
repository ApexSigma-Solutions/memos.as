# QWEN.md - memOS.as Project

## Project Overview

This project, `memos.as` (memOS), serves as the cognitive core for the DevEnviro ecosystem. It provides persistent memory and tool discovery capabilities for AI agents, transforming them from simple executors into resourceful, learning problem-solvers. It manages different memory tiers and facilitates agent collaboration through tool awareness.

## Key Technologies & Architecture

- **Core Platform**: Python 3.13, FastAPI
- **Memory Tiers**:
  - **Tier 1 (Working Memory)**: Redis for high-speed caching and temporary storage.
  - **Tier 2 (Episodic/Procedural Memory)**: PostgreSQL (structured data) and Qdrant (vector embeddings).
  - **Tier 3 (Semantic Memory)**: Neo4j (knowledge graph for concepts and relationships).
- **Observability**: OpenTelemetry (Jaeger for tracing, Prometheus for metrics), Structlog (logging), Langfuse (LLM observability).
- **Database Clients**: Custom clients for PostgreSQL, Qdrant, Redis, and Neo4j.
- **Dependency Management**: Poetry (declared in `pyproject.toml`), with dependencies listed in `requirements.txt`.

## Directory Structure

```
memos.as/
├── app/                       # Main application package
│   ├── main.py                # FastAPI application entry point and core endpoints
│   ├── models/                # Pydantic data models for requests/responses
│   ├── services/              # Database and external service clients
│   └── tests/                 # Application tests
├── config/                    # Configuration files (if any, not detailed in exploration)
├── docs/                      # Documentation (MkDocs)
├── scripts/                   # Utility scripts
├── Dockerfile                 # Application Docker image definition
├── docker-compose.yml         # Service definition (intended for unified DevEnviro stack)
├── pyproject.toml             # Poetry project configuration
├── poetry.lock                # Locked dependencies
├── requirements.txt           # List of dependencies
└── README.md                  # Project README
```

## Core Concepts

- **Memory Tiers**:
  - **Tier 1 (`/memory/1/store`)**: Stores data in Redis. Used for working memory and caching.
  - **Tier 2 (`/memory/2/store`)**: Stores data in PostgreSQL and Qdrant. Used for episodic events and procedural knowledge (like code). This is the default storage path used by `InGest-LLM.as`.
  - **Tier 3 (`/memory/3/store`)**: Stores data in Neo4j. Used for semantic knowledge and relationships between concepts.
- **Tool Discovery**: Agents can register tools they provide. Other agents can discover relevant tools by querying memory based on context.
- **Observability**: Integrated metrics and tracing to monitor service health and performance across all memory tiers.

## Building and Running

### Prerequisites

- Python 3.13
- Poetry
- Docker and Docker Compose (for containerized deployment)
- Access to PostgreSQL, Qdrant, Redis, and Neo4j instances (as configured in `docker-compose.unified.yml` or `.env`)

### Development Setup

1.  Install dependencies (managed by Poetry, but `requirements.txt` exists):
    ```bash
    # If using Poetry (preferred)
    poetry install

    # Or, if using pip with requirements.txt
    pip install -r requirements.txt
    ```
2.  Configure environment variables by creating a `.env` file (refer to `docker-compose.yml` or services for required variables like database URIs).
3.  Run the development server:
    ```bash
    python app/main.py
    # Or with uvicorn
    uvicorn app.main:app --reload
    ```

### Docker Deployment

The service is designed to run within the larger DevEnviro ecosystem using Docker Compose.

1.  Build the image:
    ```bash
    docker build -t memos-as .
    ```
2.  Run the container (typically as part of the unified stack):
    ```bash
    docker-compose up
    ```

## Key API Endpoints

- **GET /**: Health check.
- **GET /health**: Detailed health check for all connected services (PostgreSQL, Qdrant, Redis, Neo4j).
- **GET /metrics**: Prometheus metrics endpoint.
- **POST /memory/store**: Stores memory across all tiers (calls the Tier 2 logic by default).
- **POST /memory/{tier}/store**: Stores memory in a specific tier (1, 2, or 3).
- **GET /memory/{memory_id}**: Retrieves a specific memory by its ID from PostgreSQL.
- **POST /memory/query**: Performs a semantic search using Qdrant and discovers relevant tools from PostgreSQL.
- **GET /memory/search**: Simple query endpoint for searching memories.
- **POST /tools/register**: Registers a new tool capability.
- **GET /tools**: Retrieves all registered tools.
- **GET /tools/search**: Searches for tools based on a query context.
- **GET /cache/stats**: Gets Redis cache statistics.
- **DELETE /cache/clear**: Clears the Redis cache.

## Development Workflow

1.  **Modify Code**: Edit files in `app/`.
2.  **Run Tests**: Execute tests using `pytest`.
3.  **Build & Deploy**: Use `poetry build` for distribution or `docker build`/`docker-compose` for containerized deployment within the DevEnviro stack.
4.  **Interact**: Use the FastAPI docs at `http://localhost:8090/docs` (or the configured port) to interact with the API.

This `QWEN.md` provides the essential context for working with the `memos.as` project.
