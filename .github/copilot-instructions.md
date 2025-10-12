Instructions Summary
I've retrieved the key instructions for this project. Here's the comprehensive breakdown:

🎯 Current Project Context: ApexSigma MCP Server Development
Critical Protocols
⚠️ MANDATORY: OMEGA INGEST CONTEXT RETRIEVAL PROTOCOL
Before making any code changes, you MUST:

Query InGest-LLM API: http://172.26.0.12:8000/query_context
Retrieve from memOS Omega Ingest: http://172.26.0.13:8090/memory/query
Validate against immutable truth in verified infrastructure
Obtain dual verification for Tier 1 infrastructure changes
Protected Services: memOS API (172.26.0.13), Neo4j (172.26.0.14), PostgreSQL (172.26.0.2), InGest-LLM API (172.26.0.12)

🚀 Current Development Focus: PHASE 1 - MCP Infrastructure Preparation
Active Priorities
✅ Docker network configuration (172.28.0.0/16) - COMPLETE
✅ JWT authentication and service accounts - COMPLETE
✅ Rate limiting per service account - COMPLETE
✅ Langfuse tracing integration - COMPLETE
🔄 Audit logging setup - IN PROGRESS
🔄 Prometheus metrics - PENDING
🔄 Grafana dashboards - PENDING
🔄 Distributed tracing - PENDING
MCP Servers Under Development
memos-mcp-server: Memory operations (172.28.0.10)
ingest-llm-mcp-server: Data ingestion (172.28.0.11)
🔧 Essential Development Commands
Environment Setup

```bash
# Start MCP infrastructure
cd memos.as
docker-compose -f docker-compose.unified.yml up -d

# Development mode - memOS MCP
poetry install
poetry shell
poetry run uvicorn app.mcp_server:app --reload --host 0.0.0.0 --port 8091

# Quality checks
poetry run ruff check .
poetry run mypy .
poetry run pytest
```

# Start MCP infrastructurecd memos.asdocker-compose -f docker-compose.unified.yml up -d# Development mode - memOS MCPpoetry installpoetry shellpoetry run uvicorn app.mcp_server:app --reload --host 0.0.0.0 --port 8091# Quality checkspoetry run ruff check .poetry run mypy .poetry run pytest
🏗️ Architecture Overview
Service Endpoints
memOS MCP Server: http://localhost:8091 - Memory operations via MCP
InGestLLM MCP Server: http://localhost:8001 - Data ingestion via MCP
memOS API: http://localhost:8090 - Direct memory operations
InGestLLM API: http://localhost:8000 - Direct ingestion operations
Databases
PostgreSQL: Procedural memory (172.26.0.2)
Redis: Working memory & MCP session caching
Qdrant: Vector database for semantic search
Neo4j: Knowledge graphs (172.26.0.14)
Observability Stack
Langfuse: MCP tracing ✅
Prometheus: Metrics 🔄
Grafana: Dashboards 🔄
OpenTelemetry: Distributed tracing 🔄
📋 Development Guidelines
Phase 1 Completion Focus - Complete infrastructure before Phase 2/3
MAR Protocol - Multi-AI-Review for integration decisions
MCP-First Development - Design APIs for MCP integration
Security by Default - JWT auth + rate limiting on all endpoints
Audit Everything - Log all critical MCP operations
Test MCP Integration - Validate tools work with AI assistants
Monitor Performance - Use Langfuse for tracking
🔐 Security Configuration

```bash
# Service accounts for AI assistants
SERVICE_ACCOUNTS = {
    "MCP_COPILOT": "copilot-secret-token",
    "MCP_GEMINI": "gemini-secret-token",
    "MCP_QWEN": "qwen-secret-token"
}

# Rate limits: 60 requests/minute per account
```

# Service accounts for AI assistantsSERVICE_ACCOUNTS = {    "MCP_COPILOT": "copilot-secret-token",    "MCP_GEMINI": "gemini-secret-token",    "MCP_QWEN": "qwen-secret-token"}# Rate limits: 60 requests/minute per account
📂 Key Files
MCP Implementation
mcp_server.py - memOS MCP server
main.py - Underlying memOS API
pyproject.toml - Dependencies
Configuration
docker-compose.unified.yml - Service definitions
.env - API keys & secrets
Documentation
GEMINI.md - Task Master AI integration guide
CLAUDE.md, COPILOT.md, QWEN.md - Agent-specific instructions
