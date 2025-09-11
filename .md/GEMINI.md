# GEMINI.md

**Gemini Assistant Instructions for ApexSigma MCP Server Development**

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
- **Primary**: Backend service and database operations for MCP servers
- **MAR Protocol**: Act as reviewer for GitHub Copilot and Qwen Code MCP implementations
- **Verification Authority**: Full verification capability for MCP infrastructure changes
- **Current Focus**: Complete Phase 1 infrastructure and implement Phase 2 memOS MCP features

**Known Issue**: DevEnviro Gemini CLI Listener (172.26.0.0/16) currently restarting - requires investigation

**Reference**: `/project_support/secure_verified_docs/OMEGA_INGEST_LAWS.md` for complete protocols.

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

## Specialized Focus Areas
- MCP server backend development and optimization
- Database design and query optimization for MCP operations
- Service integration and middleware for MCP endpoints
- Authentication and security implementations for MCP servers
- Infrastructure automation and DevOps for MCP deployment
- Memory tier architecture and agent-specific isolation
- Omega Ingest integration with POML processing
- Cross-agent knowledge sharing via confidence-scored queries
