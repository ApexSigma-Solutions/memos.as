``` markdown
# Development Plan: memOS.as

This document provides a granular breakdown of the development tasks for the memOS.as microservice, focusing on its core responsibility as the ecosystem's memory management system.

## Milestone 1: Foundational Memory Tiers (T1 & T2) - (COMPLETE)

-   **Status:** All tasks related to the initial setup, FastAPI bootstrapping, and implementation of Redis, PostgreSQL, and Qdrant for working and episodic memory are complete and verified.

## Milestone 2: Advanced Memory Tiers (T3 & T4)

This milestone focuses on adding a knowledge graph for relational data and a chronological log for long-term learning.

### Task: Implement Tier 3 (Knowledge Graph) with Neo4j

-   **Objective:** To model the relationships between stored memories, tools, and concepts.
-   **Sub-Tasks:**
    -   [ ] **Dependency:** Add the `neo4j` Python driver to `requirements.txt`.
    -   [ ] **Service:** Create `app/services/neo4j_client.py` to encapsulate all connection logic and Cypher queries.
    -   [ ] **Data Model:** Define the core graph schema.
        -   **Nodes:** Memory, Tool, Concept, Agent.
        -   **Relationships:** `RELATED_TO`, `USES`, `MENTIONS`, `CREATED_BY`.
    -   [ ] **Integration:** Modify the `/memory/store` endpoint to perform an additional step: after storing in PostgreSQL/Qdrant, it should extract key concepts from the content and create/update corresponding nodes and relationships in Neo4j.

### Task: Develop API Endpoints for Graph Queries

-   **Objective:** To allow agents to query the knowledge graph directly.
-   **Sub-Tasks:**
    -   [ ] **Schema:** Create a Pydantic model for a structured graph query request (e.g., specifying start/end nodes and relationship types).
    -   [ ] **Endpoint:** Implement a `POST /graph/query` endpoint in `app/main.py`.
    -   [ ] **Logic:** The endpoint should translate the structured request into a Cypher query, execute it via the `neo4j_client`, and return the results.

### Task: Implement chronos.as Subsystem (Tier 4)

-   **Objective:** To create a permanent, chronological log of significant events for system-wide learning.
-   **Sub-Tasks:**
    -   [ ] **Database:** Add a new `DailyLog` table model to `app/models.py` with columns for date, `event_type` (e.g., 'SOD', 'EOD', 'COMMIT', 'MAR'), and `content` (JSONB).
    -   [ ] **Migration:** Create an Alembic migration to add the `daily_logs` table to the PostgreSQL database.
    -   [ ] **Endpoint:** Implement a `POST /log/event` endpoint to allow other services or commands (like `sod.command.as.toml`) to submit log entries.

### Task: Develop API for Historical Log Retrieval

-   **Objective:** To allow agents to review past events and learn from them.
-   **Sub-Tasks:**
    -   [ ] **Endpoint:** Implement a `GET /history` endpoint.
    -   [ ] **Querying:** The endpoint should allow filtering the `daily_logs` table by a date range and `event_type`.

```