# QWEN.md - memOS.as Project

## ⚠️ **MANDATORY: OMEGA INGEST CONTEXT RETRIEVAL PROTOCOL**

**BEFORE MAKING ANY CODE CHANGES**, you MUST:

1. **Query InGest-LLM API** for relevant context: `http://172.26.0.12:8000/query_context`
2. **Retrieve from memOS Omega Ingest**: `http://172.26.0.13:8090/memory/query`
3. **Validate against immutable truth**: Ensure changes don't conflict with verified infrastructure
4. **Obtain dual verification**: For Tier 1 infrastructure changes, require verification from another AI assistant

**Protected Services (DO NOT MODIFY WITHOUT VERIFICATION)**:
- memOS API (172.26.0.13) - Omega Ingest Guardian
- Neo4j Knowledge Graph (172.26.0.14) - Immutable concept relationships
- PostgreSQL Main (172.26.0.2) - Procedural memory
- InGest-LLM API (172.26.0.12) - Data ingestion gateway

**Your Role in MCP Server Development**:
- **Primary**: Code review and quality assurance for MCP server implementations
- **MAR Protocol**: Act as reviewer for GitHub Copilot and Gemini MCP implementations
- **Verification Authority**: Quality validation and testing for MCP infrastructure
- **Current Focus**: Validation, quality control, and Phase 3 InGestLLM MCP features

## Project Overview

This project, `memos.as` (memOS), serves as the cognitive core for the DevEnviro ecosystem with a focus on **MCP server development**. It provides persistent memory and tool discovery capabilities for AI agents through standardized Model Context Protocol (MCP) interfaces, transforming them from simple executors into resourceful, learning problem-solvers.

**Current Development Focus**: MCP server implementation for memOS and InGestLLM services. Broader ecosystem development is on hold.

## Key Technologies & Architecture

- **Core Platform**: Python 3.13, FastAPI, MCP Server Framework
- **MCP Servers**:
  - `memos-mcp-server`: Memory operations MCP server (172.28.0.10)
  - `ingest-llm-mcp-server`: Data ingestion MCP server (172.28.0.11)
- **Memory Tiers**:
  - **Tier 1 (Working Memory)**: Redis for high-speed caching and temporary storage.
  - **Tier 2 (Episodic/Procedural Memory)**: PostgreSQL (structured data) and Qdrant (vector embeddings).
  - **Tier 3 (Semantic Memory)**: Neo4j (knowledge graph for concepts and relationships).
- **MCP Infrastructure**: JWT authentication, service accounts (MCP_COPILOT, MCP_GEMINI, MCP_QWEN), rate limiting (60 req/min), audit logging
- **Observability**: OpenTelemetry (Jaeger for tracing, Prometheus for metrics), Structlog (logging), Langfuse (LLM observability).
- **Database Clients**: Custom clients for PostgreSQL, Qdrant, Redis, and Neo4j.
- **Dependency Management**: Poetry (declared in `pyproject.toml`), with dependencies listed in `requirements.txt`.

## Directory Structure

```
memos.as/
├── app/                       # Main application package
│   ├── main.py                # FastAPI application entry point and core endpoints
│   ├── mcp_server.py         # MCP server implementation for memory operations
│   ├── models/                # Pydantic data models for requests/responses
│   ├── services/              # Database and external service clients
│   └── tests/                 # Application tests
├── config/                    # Configuration files
├── docs/                      # Documentation (MkDocs)
├── scripts/                   # Utility scripts
├── Dockerfile                 # Application Docker image definition
├── docker-compose.yml         # Service definition for unified DevEnviro stack
├── pyproject.toml             # Poetry project configuration
├── poetry.lock                # Locked dependencies
├── requirements.txt           # List of dependencies
├── .github/
│   └── copilot-instructions.md # AI agent development guidelines
├── GEMINI.md                  # Gemini-specific development instructions
├── QWEN.md                    # Qwen-specific development instructions
└── README.md                  # Project README
```

## MCP Development Phases

### Phase 1: Infrastructure Preparation (Current Focus)
- ✅ Docker network configuration (172.28.0.0/16)
- ✅ JWT authentication and service accounts
- ✅ Rate limiting per service account
- ✅ Langfuse tracing integration
- 🔄 **Audit logging setup** (in progress)
- 🔄 **Prometheus metrics** (pending)
- 🔄 **Grafana dashboards** (pending)
- 🔄 **Distributed tracing** (pending)

### Phase 2: memOS MCP Extension (Next)
- Agent-specific memory tiers (MCP_GEMINI, MCP_COPILOT, etc.)
- Omega Ingest integration with POML processing
- Cross-agent knowledge sharing via confidence-scored queries
- Multi-layer caching optimization

### Phase 3: InGestLLM MCP Extension (Future)
- Tokenization pipeline with Tekken tokenizer
- Web scraping and GitHub repository ingestion
- Code-aware content extraction using AST parsing
- Token quality validation and context preservation

## Core Concepts

- **Memory Tiers**:
  - **Tier 1 (`/memory/1/store`)**: Stores data in Redis. Used for working memory and caching.
  - **Tier 2 (`/memory/2/store`)**: Stores data in PostgreSQL and Qdrant. Used for episodic events and procedural knowledge (like code). This is the default storage path used by `InGest-LLM.as`.
  - **Tier 3 (`/memory/3/store`)**: Stores data in Neo4j. Used for semantic knowledge and relationships between concepts.
- **MCP Tools**: Standardized tools for memory operations accessible by AI assistants
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
    # Main memOS API
    python app/main.py
    # Or with uvicorn
    uvicorn app.main:app --reload

    # MCP Server
    uvicorn app.mcp_server:app --reload --host 0.0.0.0 --port 8091
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

### Core memOS Endpoints
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

### MCP Server Endpoints
- **GET /mcp/health**: MCP server health check
- **POST /mcp/tools/store_memory**: MCP tool for storing memory
- **POST /mcp/tools/query_memory**: MCP tool for querying memory
- **POST /mcp/tools/register_tool**: MCP tool for registering tools
- **GET /mcp/tools/list**: MCP tool for listing available tools

## Development Workflow

1.  **Modify Code**: Edit files in `app/`, focusing on MCP server implementation.
2.  **Run Tests**: Execute tests using `pytest`.
3.  **Build & Deploy**: Use `poetry build` for distribution or `docker build`/`docker-compose` for containerized deployment within the DevEnviro stack.
4.  **Interact**: Use the FastAPI docs at `http://localhost:8090/docs` (main API) or `http://localhost:8091/docs` (MCP server) to interact with the APIs.
5.  **Quality Assurance**: Follow MAR protocol - get reviews from other AI assistants before integration.

## MCP Server Build Plan Reference

See `MCP Server Build Plan memOS & InGestLLM.yml` for the complete development roadmap and current task status.

This `QWEN.md` provides the essential context for working with the `memos.as` MCP server development project.
