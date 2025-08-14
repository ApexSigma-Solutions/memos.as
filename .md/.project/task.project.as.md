``` markdown
# Project Tasks: memOS.as

This file tracks the specific, actionable tasks for the current development cycle, derived from the project plan.

## Milestone 2: Advanced Memory Tiers (T3 & T4)

### Implement Tier 3 (Knowledge Graph) with Neo4j

*   [x] **Dependency:** Add neo4j Python driver to requirements.txt.
*   [x] **Service:** Create app/services/neo4j_client.py to encapsulate connection logic and Cypher queries.
*   [x] **Data Model:** Define the core graph schema (Nodes: Memory, Tool, Concept, Agent; Relationships: RELATED_TO, USES, MENTIONS, CREATED_BY).
*   [ ] **Integration:** Modify /memory/store endpoint to extract concepts and update the Neo4j graph after storing data in PostgreSQL/Qdrant.

### Develop API Endpoints for Graph Queries

*   [ ] **Schema:** Create a Pydantic model for a structured graph query request.
*   [ ] **Endpoint:** Implement POST /graph/query in app/main.py.
*   [ ] **Logic:** Implement the translation from the Pydantic request model to a dynamic Cypher query.

### Implement chronos.as Subsystem (Tier 4)

*   [ ] **Database:** Add a DailyLog table model to app/models.py (date, event_type, content).
*   [ ] **Migration:** Create and apply an Alembic migration script to add the daily_logs table.
*   [ ] **Endpoint:** Implement POST /log/event to allow other services to submit log entries.

### Develop API for Historical Log Retrieval

*   [ ] **Endpoint:** Implement GET /history.
*   [ ] **Querying:** Add logic to filter historical logs by a date range and event_type.

```