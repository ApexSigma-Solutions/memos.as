# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`memos.as` is a FastAPI microservice that serves as the central memory and tool discovery hub for the DevEnviro AI agent ecosystem. It provides persistent memory capabilities and tool awareness to transform agents from simple executors into learning problem-solvers.

## Architecture & Database Design

The service uses a sophisticated multi-tiered database architecture:

- **PostgreSQL**: Primary database with complex schema including:
  - Context management (`active_context`, `product_context` with versioned history)
  - Decision tracking with full-text search via SQLite FTS5
  - Progress entries with hierarchical relationships
  - Custom data storage with category-based organization
  - Context linking system for relationship mapping
- **Qdrant**: Vector database for semantic search of episodic memories
- **Redis**: High-speed working memory and caching layer

The database schema includes sophisticated features like FTS5 virtual tables with automatic triggers for search indexing, context versioning, and relational linking between different data types.

## Development Setup

### Environment Management
Use `uv` for Python environment management:
```bash
# Create and activate virtual environment
uv venv && uv pip install -r requirements.txt

# Windows activation
.venv\Scripts\activate

# macOS/Linux activation  
source .venv/bin/activate
```

### Database Migrations
The project uses Alembic for database migrations with dynamic URL configuration:
```bash
# Database URL is set dynamically by ConPort's run_migrations function
# Migration files are in context_portal/alembic/versions/
```

## Key Components

### API Models (`app/models.py`)
- `StoreRequest`: For memory storage operations
- `QueryRequest`: For memory retrieval with configurable top_k results  
- `ToolRegistrationRequest`: For tool discovery system

### Service Clients (`app/services/`)
- `postgres_client.py`: SQLAlchemy-based PostgreSQL integration
- `qdrant_client.py`: Vector database client for semantic search
- `redis_client.py`: Redis client for working memory operations

### Context Portal
The `context_portal/` directory contains the database migration system and vector data storage, with Alembic managing schema evolution and relationship mapping.

## ConPort Agent Memory Protocol

This project implements the ConPort Agent Memory Protocol - a mandatory set of rules for AI agent interaction with the shared memory system.

### Session Initialization Protocol (MANDATORY)
Every agent session must begin with:
1. **Check for existing context**: Look for `context.db` file in workspace
2. **Load existing context**: If found, retrieve and load project context
3. **Dynamic context retrieval**: Use RAG strategy with FTS and semantic search

### Core Protocol Rules
- **Retrieve First, Store Last**: Always check existing memory before storing new information
- **User Confirmation Required**: All write/update/delete operations need explicit user approval
- **Proactive Knowledge Management**: Identify and suggest logging decisions, progress, and relationships

### Memory System Integration
When working with the byterover-mcp system:
- Always use `byterover-retrieve-knowledge` before starting tasks to get relevant context
- Always use `byterover-store-knowledge` to store critical information after successful task completion

### Society of Agents Collaboration
The system supports role-based collaboration:
- **@Claude**: Architect role
- **@Gemini**: Implementer role  
- **@Qodo**: QA role
- **Mandatory Agent Review (MAR)**: All artifacts require review and approval before integration

## Development Status

This is an active development project with scaffolded structure. Key missing components that may need implementation:
- Main FastAPI application file (`app/main.py`)
- Service client implementations (currently empty files)
- Docker configuration files
- Testing framework setup

The database schema is fully defined and includes advanced features like full-text search triggers and context versioning systems.