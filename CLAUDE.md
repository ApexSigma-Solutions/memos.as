# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

**Reference**: `/project_support/secure_verified_docs/OMEGA_INGEST_LAWS.md` for complete protocols.

## Project Overview

ApexSigmaProjects.Dev is a unified development environment for the **ApexSigma "Society of Agents" Ecosystem** - a multi-agent AI collaboration platform. The workspace contains four interconnected microservices that form a complete agentic development environment where specialized AI agents collaborate on complex development tasks.

## Project Architecture

### Core Projects
- **devenviro.as**: Main orchestrator for AI Society of Agents (FastAPI, PostgreSQL, Redis, Qdrant, Neo4j, RabbitMQ)
- **InGest-LLM.as**: Intelligent content ingestion engine (FastAPI, OpenTelemetry, Langfuse)
- **memos.as**: Knowledge management system (FastAPI, PostgreSQL, Qdrant, Redis)
- **tools.as**: Development utilities and tool registry (FastAPI, SQLAlchemy, PostgreSQL)
- **embedding-agent.as**: Vector embedding service with Redis caching

### Infrastructure
All services deploy via **unified Docker stack** (`docker-compose.unified.yml`) with 17+ integrated services including monitoring stack (Grafana, Prometheus, Jaeger, Loki) and full observability via Langfuse.

## Development Commands

### Prerequisites
- Python 3.13+
- Docker Desktop
- Poetry for dependency management

### Project Startup
```bash
# Start unified infrastructure (all services)
docker-compose -f docker-compose.unified.yml up -d

# Check service health
docker-compose -f docker-compose.unified.yml ps

# View observability dashboard
# Open http://localhost:3000 (Langfuse)
```

### Per-Project Development

#### devenviro.as (Main Orchestrator)
```bash
# Development mode
cd devenviro.as
pip install -r requirements.txt
python app/src/main.py

# Database operations
cd app && python -c "from src.core.migrations_runner import apply_migrations; apply_migrations()"
cd app && python src/seed_knowledge.py

# Individual tests (no unified test runner)
cd app && python tests/test_telemetry_stack.py
cd app && python tests/test_review_manager.py
```

#### InGest-LLM.as (Content Ingestion)
```bash
# Poetry development
cd InGest-LLM.as
poetry install && poetry shell
poetry run uvicorn src.ingest_llm_as.main:app --reload

# Code quality
poetry run ruff check . && poetry run ruff format .
poetry run mypy src/

# Testing
poetry run pytest
poetry run pytest --cov=src/ingest_llm_as
```

#### memos.as & tools.as
```bash
# Poetry setup
cd memos.as  # or tools.as
poetry install && poetry shell

# Development
poetry run uvicorn app.main:app --reload

# Quality checks
poetry run ruff check .
poetry run pytest
```

### Documentation System
```bash
# Build all project documentation (unified builder)
python scripts/build_ecosystem_docs.py build

# Serve specific project docs
python scripts/build_ecosystem_docs.py serve devenviro.as
python scripts/build_ecosystem_docs.py serve InGest-LLM.as
python scripts/build_ecosystem_docs.py serve memos.as
python scripts/build_ecosystem_docs.py serve tools.as

# Individual project documentation
cd [project] && mkdocs serve    # Development
cd [project] && mkdocs build    # Production
```

## Key Development Patterns

### Multi-Agent Architecture
The DevEnviro orchestrator manages 12+ specialized AI agent personas:
- **backend-specialist**, **frontend-specialist**, **devops-engineer**
- **qa-engineer**, **security-engineer**, **software-architect**
- **product-owner**, **project-manager**, **engineering-manager**
- **enterprise-cto**, **technical-writer**, **senior-fullstack-developer**

### Memory Protocol (memos.as)
All AI agents follow standardized memory interaction patterns:
1. **Session Initialization**: Check existing context, load project state
2. **Retrieve First, Store Last**: Query memory before storing
3. **User Confirmation Required**: All write/update/delete operations need approval
4. **Dynamic Context Retrieval**: RAG with full-text search and semantic search

### Society of Agents Collaboration
- **@Claude**: Architect role
- **@Gemini**: Implementer role
- **@Qodo**: QA role
- **Mandatory Agent Review (MAR)**: All artifacts require review before integration

### Message Flow
1. Tasks → FastAPI orchestrator (devenviro.as)
2. Orchestrator analyzes and delegates to agents
3. Agents communicate via RabbitMQ message queue
4. Memory operations → memos.as
5. Tool discovery → tools.as
6. Data ingestion → InGest-LLM.as

## Service Integration

### Database Layer
- **Redis**: Working memory and caching
- **PostgreSQL**: Procedural memory with complex schemas
- **Qdrant**: Vector database for episodic/semantic search
- **Neo4j**: Semantic relationships and knowledge graphs

### Service Endpoints
- **DevEnviro API**: http://localhost:8090 (/docs)
- **InGest-LLM**: http://localhost:8000 (/health)
- **Grafana**: http://localhost:8080 (admin/devenviro123)
- **Prometheus**: http://localhost:9090
- **Jaeger**: http://localhost:16686
- **RabbitMQ**: http://localhost:15672

### Observability Stack
- **OpenTelemetry**: Distributed tracing across all services
- **Prometheus**: Metrics collection and monitoring
- **Grafana**: Dashboards and visualization
- **Jaeger**: Request tracing and performance monitoring
- **Loki**: Centralized logging
- **Langfuse**: LLM-specific observability (347+ active traces)

## Development Notes

### Database Migrations
DevEnviro migrations are in `app/migrations/`:
- `001_create_agent_communications.sql`: Message routing
- `002_knowledge_documents.sql`: Knowledge storage
- `003_create_agents_table.sql`: Agent registry
- `004_add_token_to_agent.sql`: Authentication
- `005_add_capabilities_to_agents.sql`: Agent capabilities

### Context Portal System
Each project has `context_portal/` containing:
- **Alembic migrations**: Database schema evolution
- **Vector data**: ChromaDB/Qdrant collections
- **Context databases**: SQLite context storage

### Modern Python Toolchain
All projects use:
- **Ruff**: Linting and formatting
- **mypy**: Static type checking
- **Poetry**: Dependency management
- **pre-commit**: Automated quality checks
- **pytest**: Testing framework

## Project Status & Integration

### Current State
- **devenviro.as**: ✅ Active development, full orchestration system operational
- **InGest-LLM.as**: ✅ Core ingestion pipeline operational with observability
- **memos.as**: ✅ Production-ready with progress logging
- **tools.as**: ✅ Core functionality operational
- **Infrastructure**: ✅ 17+ services, 17+ hour stable uptime

### Key Integration Points
- All services integrate through DevEnviro orchestrator
- Memory operations centralized through memos.as memory protocol
- Tool discovery handled by tools.as registry
- Data flows processed through InGest-LLM.as pipelines
- Full observability stack provides end-to-end monitoring

## Development Workflow

When working in this workspace:
1. **Use unified Docker stack** for infrastructure
2. **Follow memory protocol** for context operations
3. **Leverage observability stack** for monitoring
4. **Respect modular architecture** - each service has specific role
5. **Document as you code** - update docstrings and markdown for automatic docs
6. **Test individually per project** - no workspace-wide test runner

The ecosystem represents a complete AI development platform where agents learn, remember, and collaborate to solve complex development challenges through structured multi-agent workflows.
