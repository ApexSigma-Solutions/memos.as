```markdown
# AGENT.md

This file provides guidance to AI agents when working with code in this repository.

## Project Overview

This project, devenviro.as, is a modular, agentic AI-supported development environment. It implements a **"Society of Agents"** architecture where specialized AI agents collaborate on complex development tasks, orchestrated by a central service. The primary goal is to improve developer Quality of Life (QoL) by creating persistent, context-aware AI partners that reduce cognitive load and automate workflows. [cite: devenviro.as/.md/.project/brief.project.md]

A foundational principle is **"Hierarchical Context is King."** All agent actions must be grounded in the project's documentation stored in the .md/ directories, which serve as the single source of truth for architecture, rules, and tasks. [cite: devenviro.as/.md/.rules/global.rules.md]

## Architecture

The system's core is a collection of containerized microservices that enable the "Society of Agents" to communicate, remember, and collaborate effectively.

### Core Components

-   **Orchestrator**: The central nervous system, a **FastAPI** service that decomposes user requests into tasks and delegates them to the appropriate agents. The core logic is in app/src/core/orchestrator.py. [cite: devenviro.as/.md/.agent/master_conductor.agent.md]
-   **Agent Registry**: Manages the lifecycle, registration, and capabilities of all specialized AI agent personas. See app/src/core/agent_registry.py and app/src/core/enhanced_initialization_manager.py.
-   **Message Queue**: **RabbitMQ** serves as the asynchronous communication backbone for all inter-agent messaging, ensuring decoupled and resilient interactions. The CommunicationsManager at app/src/core/communications_manager.py handles message routing and logging. [cite: devenviro.as/.md/.project/techstack.project.md]
-   **Multi-Tiered Memory Engine**:
    -   **PostgreSQL**: Acts as the **episodic memory**, storing all agent communications in the agent_communications table for audit and recall. The DatabaseManager (app/src/core/database_manager.py) is a thread-safe singleton for all database interactions. [cite: devenviro.as/.md/.agent/master_conductor.agent.md]
    -   **Redis**: High-speed **working memory** for session state and caching. [cite: devenviro.as/.md/.project/techstack.project.md]
    -   **Qdrant**: A vector database for **semantic memory**, enabling semantic search on agent experiences. [cite: devenviro.as/.md/.project/techstack.project.md]
-   **Observability Stack**: A comprehensive telemetry system using **OpenTelemetry** with Jaeger for traces, Prometheus for metrics, and Loki for logs. Grafana provides a unified dashboard for visualization. [cite: devenviro.as/docker-compose.yml, devenviro.as/.md/.agent/master_conductor.agent.md]

## Key Directories

-   **.md/**: The knowledge base for the entire project, containing rules, agent personas, project plans, and architecture documents. **This is the primary source of truth.**
-   **app/src/core/**: Contains the primary business logic for the Orchestrator, database management, communication, and agent initialization.
-   **app/migrations/**: SQL files for setting up the database schema.
-   **app/Workflows/**: Defines multi-agent collaborative processes, such as the author_reviewer_workflow.py.
-   **config/**: Contains configuration files for infrastructure services like Prometheus, Grafana, and Loki.

## Development Commands

The project is designed to be run using Docker and Docker Compose. Environment variables are managed with standard .env files.

### Environment Setup

```bash
# Environment variables are configured in .env files
# For Docker deployment: .env.docker
# For local development: .env

# Edit the appropriate .env file with your configuration values
```

### Running the Full Stack

``` bash
# Build and start all services, including the telemetry stack, in detached mode
docker-compose up --build -d

```

### Database Operations

The devenviro-api service automatically runs migrations and seeds the knowledge base on startup.

  - **Migrations**: SQL files in app/migrations/ are applied by app/src/core/migrations\_runner.py.
  - **Knowledge Seeding**: Markdown files from the .md/ directory are loaded into the knowledge\_documents table by app/src/core/seed\_knowledge.py.

## Testing & Demos

``` bash
# Run the comprehensive telemetry stack validation test
python app/tests/test_telemetry_stack.py

# Run a demonstration of the agent communication system and workflow manager
python app/src/demo_agent_communication.py

```

## Service Ports

  - **API (Orchestrator)**: http://localhost:8090 (API Docs at /docs)
  - **Grafana**: http://localhost:8080 (Default login: admin/devenviro123) \[cite: devenviro.as/docker-compose.yml, devenviro.as/config/grafana.ini\]
  - **Prometheus**: http://localhost:9090
  - **Jaeger Tracing**: http://localhost:16686
  - **RabbitMQ Management**: http://localhost:15672
  - **PostgreSQL**: localhost:5432
  - **Redis**: localhost:6379
  - **Qdrant UI**: http://localhost:6333

## Common Development Patterns

### Agent System

The system is built around specialized, persona-driven agents defined as markdown files in .md/.agent/.personas/. The EnhancedInitializationManager loads these files at startup, registers the agents in the database, and establishes their communication listeners via RabbitMQ. \[cite: devenviro.as/app/src/core/enhanced\_initialization\_manager.py\]

### Message Flow

1.  A user request or internal trigger initiates a task in the **Orchestrator**.
2.  The Orchestrator decomposes the task into a WorkflowPlan consisting of multiple TaskNodes. \[cite: devenviro.as/app/src/core/orchestrator.py\]
3.  The Orchestrator selects the best-suited agent from the AgentRegistry based on capabilities and current workload.
4.  A task is delegated to an agent via a structured AgentMessage sent through the **RabbitMQ** message queue.
5.  All messages are automatically logged to the PostgreSQL agent\_communications table for persistence and audit. \[cite: devenviro.as/app/src/core/communications\_manager.py\]
6.  Upon task completion, the agent sends a TASK\_RESULT message back to the Orchestrator, which then proceeds with the next step in the workflow.

<!-- end list -->

```

```
