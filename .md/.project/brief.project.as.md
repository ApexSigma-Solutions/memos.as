``` markdown
# Project Brief: MemOS (Memory Operating System)

Project Code: memos.as

Parent Ecosystem: DevEnviro

Version: 1.1

## 1. The Problem: Agent Amnesia & Tool Blindness

For an AI "Society of Agents" to be effective, its members must be able to learn from experience and know what capabilities are at their disposal. Currently, agents within the DevEnviro ecosystem are powerful but suffer from two critical limitations:

*   **Amnesia:** They are stateless, treating every task as their first. They cannot recall past decisions, successful solutions, or user feedback, leading to repetitive work and inconsistent outputs.
*   **Tool Blindness:** They are unaware of the specialized tools available to them. The burden falls on the Orchestrator to manually inject tool information, making the system less autonomous and scalable.

This creates a cognitive bottleneck, limiting the society's ability to evolve and solve complex problems with true intelligence.

## 2. The Vision: A Cognitive Core for a Learning Society

The MemOS (Memory Operating System) is designed to be the central cognitive core for the entire DevEnviro ecosystem. It will provide a unified, intelligent service that endows agents with a persistent memory and an active awareness of their available tools.

Our vision is to transform agents from simple task-executors into resourceful, learning problem-solvers that can autonomously leverage past knowledge and available capabilities to achieve their goals more effectively.

## 3. The Solution: A Unified Memory & Tool Discovery Service

MemOS will be a standalone FastAPI microservice that provides a simple, powerful API for three primary functions:

1.  **Memory Management:** It will offer store and query endpoints, abstracting the complexity of the multi-tiered memory engine (Qdrant for semantic search, PostgreSQL for logging). Agents will have a single, reliable interface to persist and retrieve experiential knowledge.
2.  **Tool Discovery:** It will maintain a dynamic registry of all available tools within the ecosystem. When an agent queries the MemOS, it will receive not only relevant memories but also a list of tools that can help solve the task at hand.
3.  **Knowledge Ingestion:** The ecosystem will include a new service, **InGest-LLM**, which will be operated by a specialized local agent (**Cortex Agent**). This service will automatically scan codebases (extracting docstrings), websites, and other data stores, parsing the information and feeding it into the MemOS to continuously build the society's knowledge base.

By creating MemOS as a separate, dedicated service, we ensure a clean, decoupled architecture that allows the cognitive capabilities of our agent society to be developed and scaled independently.

```