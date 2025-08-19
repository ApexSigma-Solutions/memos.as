# Welcome to memOS.as Documentation

memOS.as is a FastAPI microservice that serves as the central memory and tool discovery hub for the DevEnviro AI agent ecosystem. It provides persistent memory capabilities and tool awareness to transform agents from simple executors into learning problem-solvers.

## Features

- **Multi-tier Memory Architecture**: Redis (working memory), PostgreSQL (structured storage), Qdrant (vector search)
- **Tool Discovery System**: Register and discover tools across the ecosystem
- **Semantic Memory Search**: Vector-based similarity search for episodic memories
- **ConPort Agent Memory Protocol**: Standardized protocol for AI agent memory interaction

## Quick Start

1. **Setup Environment**: Configure your database connections and API keys
2. **Start Services**: Run Redis, PostgreSQL, and Qdrant using Docker Compose
3. **Run memOS.as**: Start the FastAPI application
4. **Register Tools**: Use the `/tools/register` endpoint to add available tools
5. **Store Memories**: Use the `/memory/store` endpoint to save information
6. **Query Memories**: Use the `/memory/query` endpoint for semantic search

## Architecture

memOS.as implements a sophisticated multi-tiered memory system:

### Tier 1: Working Memory (Redis)
- High-speed cache for frequently accessed data
- Session state management
- Temporary storage for processing workflows

### Tier 2: Episodic Memory (PostgreSQL + Qdrant)
- **PostgreSQL**: Structured storage with full-text search capabilities
- **Qdrant**: Vector database for semantic similarity matching
- Bidirectional linking between structured and vector data

### Future Tiers
- **Tier 3**: Knowledge Graph (Neo4j) - Conceptual relationships
- **Tier 4**: Historical Logs (chronos.as) - Long-term event tracking

## Navigation

- **[Tutorials](tutorials/index.md)**: Step-by-step guides to get started
- **[How-To Guides](how-to/index.md)**: Practical solutions for common tasks
- **[API Reference](reference/index.md)**: Complete API documentation and technical details