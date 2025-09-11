# Plan: memOS MCP Server - Phase 1 (Baseline Functionality)

**Objective:** To implement the minimum required functionality to turn the memOS.as service into a discoverable MCP server capable of storing and recalling memories for connected agents, governed by the Mandatory Agent Review (MAR) protocol.

## Phase 0: Environment & Prerequisite Verification

- [ ] **Task 0.1:** Verify that the memOS.as container builds and runs without errors in the unified Docker stack.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

- [ ] **Task 0.2:** Confirm network connectivity from a test client container to the memOS.as container within the 172.26.0.0/16 network.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

- [ ] **Task 0.3:** Verify database connectivity from within the memOS.as container to the PostgreSQL and Neo4j services.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

- [ ] **Task 0.4:** Confirm the etcd service is running and accessible from the memOS.as container.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

## Phase 1: API Endpoint Implementation (memOS.as)

- [ ] **Task 1.1:** Define API Schemas for /store, /recall, and standard responses.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

- [ ] **Task 1.2:** Implement a basic HTTP/2 server within the memOS.as Python application.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

- [ ] **Task 1.3:** Create /store and /recall endpoint stubs with schema validation.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

- [ ] **Task 1.4:** Integrate and apply JWT authentication middleware to the new endpoints.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

## Phase 2: Data Persistence Logic (memOS.as)

- [ ] **Task 2.1:** Implement the database transaction logic for the /store endpoint (Neo4j & PostgreSQL).
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

- [ ] **Task 2.2:** Implement the database query logic for the /recall endpoint (Neo4j text search with filtering).
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

## Phase 3: Service Discovery (memOS.as)

- [ ] **Task 3.1:** Integrate the etcd3 client library into memOS.as dependencies.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

- [ ] **Task 3.2:** Implement service registration with etcd on application startup, including a TTL.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

- [ ] **Task 3.3:** Implement a heartbeat mechanism to periodically refresh the service's TTL lease in etcd.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

## Phase 4: Agent Client & E2E Test

- [ ] **Task 4.1:** Develop a simple Python MCPClient class for agents to use.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

- [ ] **Task 4.2:** Implement service discovery logic within the MCPClient to find memOS.as via etcd.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

- [ ] **Task 4.3:** Implement `store_memory()` and `recall_memory()` methods in the MCPClient.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do

- [ ] **Task 4.4:** Write and execute an end-to-end test script (test\_mcp.py) to validate the entire workflow.
  
    - **Assignee (Implementer):** Gemini
    - **Reviewer:** Github (MAR Protocol)
    - **Status:** To Do
