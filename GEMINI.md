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

## ConPort Agent Memory Protocol

This project implements the ConPort Agent Memory Protocol - a mandatory set of rules for AI agent interaction with the shared memory system.

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
When working with the byterover-mcp system:
- Always use `byterover-retrieve-knowledge` before starting tasks to get relevant context
- Always use `byterover-store-knowledge` to store critical information after successful task completion

### Society of Agents Collaboration
The system supports role-based collaboration:
- **@Claude**: Architect role
- **@Gemini**: Implementer role  
- **@Qodo**: QA role
- **Mandatory Agent Review (MAR)**: All artifacts require review and approval before integration
