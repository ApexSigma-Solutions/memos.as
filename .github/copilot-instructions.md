# GitHub Copilot Instructions for ApexSigma MCP Server Development

## ⚠️ **MANDATORY: OMEGA INGEST CONTEXT RETRIEVAL PROTOCOL**

**BEFORE MAKING ANY CODE CHANGES**, you MUST:
1. Query InGest-LLM API: `http://172.26.0.12:8000/query_context`
2. Retrieve from memOS Omega Ingest: `http://172.26.0.13:8090/memory/query`
3. Validate against immutable truth in verified infrastructure
4. Obtain dual verification for Tier 1 infrastructure changes

**Protected Services**: memOS API (172.26.0.13), Neo4j (172.26.0.14), PostgreSQL (172.26.0.2), InGest-LLM API (172.26.0.12)

## Current Development Focus

**PHASE 1: MCP Infrastructure Preparation** (Active Development)
- Currently focused on implementing MCP servers for memOS and InGestLLM
- Broader ecosystem development (devenviro.as, tools.as, embedding-agent.as) is on hold
- Priority: Complete remaining Phase 1 infrastructure tasks before advancing

**Key Priorities**:
- Complete audit logging setup (1.8)
- Implement MCP-specific Prometheus metrics (1.10)
- Configure Grafana dashboards for MCP monitoring (1.11)
- Set up distributed tracing for MCP operations (1.12)

## MCP Server Architecture

**Two MCP Servers Under Development**:
- `memos-mcp-server`: Memory operations MCP server (172.28.0.10)
- `ingest-llm-mcp-server`: Data ingestion MCP server (172.28.0.11)

**Infrastructure**:
- Dedicated Docker network: `apexsigma_net` (172.28.0.0/16)
- JWT authentication with service accounts (MCP_COPILOT, MCP_GEMINI, MCP_QWEN)
- Rate limiting: 60 requests/minute per service account
- Audit logging for all critical operations
- Langfuse tracing for MCP-specific operations

## Development Workflows

### Environment Setup
```bash
# Start MCP infrastructure (focus on memOS and InGestLLM services)
cd memos.as && docker-compose -f docker-compose.unified.yml up -d

# Development mode for MCP servers
cd memos.as && poetry install && poetry shell
poetry run uvicorn app.mcp_server:app --reload --host 0.0.0.0 --port 8091

# InGestLLM MCP server
cd InGest-LLM.as && poetry install && poetry shell
poetry run uvicorn src.ingest_llm_as.mcp_server:app --reload --host 0.0.0.0 --port 8001
```

### Critical Commands
- **MCP Infrastructure**: `docker-compose -f docker-compose.unified.yml up -d`
- **memOS MCP Development**: `poetry run uvicorn app.mcp_server:app --reload --port 8091`
- **InGestLLM MCP Development**: `poetry run uvicorn src.ingest_llm_as.mcp_server:app --reload --port 8001`
- **Quality Checks**: `poetry run ruff check . && poetry run mypy . && poetry run pytest`

## MCP Development Patterns

### Authentication & Security
```python
# JWT authentication for MCP endpoints
from fastapi.security import HTTPBearer
from jose import jwt

security = HTTPBearer()

# Service accounts for AI assistants
SERVICE_ACCOUNTS = {
    "MCP_COPILOT": "copilot-secret-token",
    "MCP_GEMINI": "gemini-secret-token",
    "MCP_QWEN": "qwen-secret-token"
}

# Rate limiting per service account
RATE_LIMITS = {
    "MCP_COPILOT": 60,  # requests per minute
    "MCP_GEMINI": 60,
    "MCP_QWEN": 60
}
```

### MCP Server Structure
```python
from mcp.server import Server
from fastapi import FastAPI

# Initialize MCP server
server = Server("memos-mcp-server")

# FastAPI app for MCP over HTTP
app = FastAPI(
    title="memOS MCP Server",
    description="MCP server for memory operations"
)

# Register MCP tools
@server.tool()
async def store_memory(content: str, metadata: dict) -> str:
    """Store memory with MCP-specific handling"""
    # Implementation here
    pass

@server.tool()
async def query_memory(query: str) -> dict:
    """Query memory with MCP-specific handling"""
    # Implementation here
    pass
```

### Audit Logging
```python
# Structured audit logging for MCP operations
import logging
import json

audit_logger = logging.getLogger("mcp_audit")
audit_formatter = logging.Formatter(
    json.dumps({
        "timestamp": "%(asctime)s",
        "level": "%(levelname)s",
        "service": "memOS-MCP",
        "event": "%(message)s"
    })
)
```

## Integration Points

### MCP Service Endpoints
- **memOS MCP Server**: `http://localhost:8091` (/docs) - Memory operations via MCP
- **InGestLLM MCP Server**: `http://localhost:8001` (/docs) - Data ingestion via MCP
- **memOS API**: `http://localhost:8090` (/docs) - Direct memory operations
- **InGestLLM API**: `http://localhost:8000` (/health) - Direct ingestion operations

### Database Connections (MCP Context)
- **PostgreSQL**: Procedural memory with MCP-specific schemas
- **Redis**: Working memory and MCP session caching
- **Qdrant**: Vector database for MCP semantic search
- **Neo4j**: Knowledge graphs for MCP relationship queries

### Observability (MCP Focus)
- **Langfuse**: MCP-specific tracing and performance monitoring
- **Prometheus**: MCP metrics collection (pending implementation)
- **Grafana**: MCP dashboards (pending configuration)
- **OpenTelemetry**: Distributed tracing for MCP operations (pending)

## Key Files & Directories

### MCP Server Implementation
- `memos.as/app/mcp_server.py`: memOS MCP server implementation
- `InGest-LLM.as/src/ingest_llm_as/mcp_server.py`: InGestLLM MCP server implementation
- `memos.as/app/main.py`: Underlying memOS API that MCP server uses
- `InGest-LLM.as/src/ingest_llm_as/main.py`: Underlying InGestLLM API

### Configuration
- `memos.as/pyproject.toml`: Dependencies including MCP server libraries
- `InGest-LLM.as/pyproject.toml`: Dependencies for ingestion MCP server
- `docker-compose.unified.yml`: MCP service definitions with static IPs

### Documentation
- `MCP Server Build Plan memOS & InGestLLM.yml`: Current development roadmap
- `CLAUDE.md`, `COPILOT.md`, `GEMINI.md`, `QWEN.md`: Agent-specific instructions

## Development Guidelines

1. **Focus on Phase 1 Completion**: Complete remaining infrastructure tasks before Phase 2/3
2. **Follow MAR Protocol**: Get reviews from other AI assistants before integration
3. **MCP-First Development**: Design APIs with MCP integration in mind
4. **Security by Default**: Implement authentication and rate limiting for all MCP endpoints
5. **Audit Everything**: Log all critical MCP operations for compliance and debugging
6. **Test MCP Integration**: Validate MCP tools work correctly with AI assistants
7. **Monitor Performance**: Use Langfuse to track MCP operation performance and errors

## Current Task Priorities

**Immediate Focus (Phase 1 Infrastructure)**:
- ✅ Docker network configuration (172.28.0.0/16)
- ✅ JWT authentication and service accounts
- ✅ Rate limiting per service account
- ✅ Langfuse tracing integration
- 🔄 **Audit logging setup** (in progress)
- 🔄 **Prometheus metrics** (pending)
- 🔄 **Grafana dashboards** (pending)
- 🔄 **Distributed tracing** (pending)

**Future Phases** (On Hold):
- Phase 2: memOS MCP Extension (memory tiers, Omega Ingest integration)
- Phase 3: InGestLLM MCP Extension (tokenization, web scraping, validation)

The current development focuses exclusively on building robust MCP server infrastructure for secure, monitored AI agent integration with memOS and InGestLLM services.</content>
<parameter name="filePath">c:\Users\steyn\ApexSigmaProjects.Dev\MCP_Server_Builds\memos.as\.github\copilot-instructions.md
