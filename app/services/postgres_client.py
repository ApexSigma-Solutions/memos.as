import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import JSON, Column, DateTime, Integer, String, Text, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

Base = declarative_base()


class Memory(Base):
    """
    Core memory table for storing episodic memories with metadata.
    This is the primary storage for the /memory/store endpoint.
    """

    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    memory_metadata = Column(
        JSON, nullable=True
    )  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    embedding_id = Column(String(255), nullable=True)  # Reference to Qdrant vector ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RegisteredTool(Base):
    """
    Tool registry table for storing available tools and their capabilities.
    Used for tool discovery in the /memory/query endpoint.
    """

    __tablename__ = "registered_tools"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    usage = Column(Text, nullable=False)
    tags = Column(JSON, nullable=True)  # Store tags as JSON array
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class PostgresClient:
    """
    PostgreSQL client for memOS.as memory and tool management.

    This client handles:
    - Storing and retrieving episodic memories
    - Managing the tool registry
    - Linking memories with vector embeddings stored in Qdrant
    """

    def __init__(self):
        # Check for DATABASE_URL first (Docker override)
        self.database_url = os.environ.get("DATABASE_URL")

        if not self.database_url:
            # Fall back to individual environment variables
            self.host = os.environ.get("POSTGRES_HOST", "localhost")
            self.port = int(os.environ.get("POSTGRES_PORT", 5432))
            self.database = os.environ.get("POSTGRES_DB", "memos")
            self.user = os.environ.get("POSTGRES_USER", "apexsigma_user")
            self.password = os.environ.get(
                "POSTGRES_PASSWORD", "your_secure_postgres_password_here"
            )

            self.database_url = (
                f"postgresql://{self.user}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}"
            )

        self.engine = create_engine(self.database_url, echo=False)
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def get_session(self) -> Session:
        """Context manager for database sessions with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    # Memory Management (for /memory/store and /memory/query endpoints)
    def store_memory(
        self,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_id: Optional[str] = None,
    ) -> Optional[int]:
        """
        Store a new memory entry.

        Args:
            content: The memory content to store
            metadata: Optional metadata dictionary
            embedding_id: Optional reference to Qdrant vector ID

        Returns:
            Memory ID if successful, None if failed
        """
        try:
            with self.get_session() as session:
                memory = Memory(
                    content=content, memory_metadata=metadata, embedding_id=embedding_id
                )
                session.add(memory)
                session.flush()  # Flush to get the ID but don't commit yet
                memory_id = memory.id

                if memory_id is None:
                    print("⚠️  Memory ID is None after flush - database issue")
                    return None

                print(f"✅ Successfully stored memory with ID: {memory_id}")
                return memory_id
        except Exception as e:
            print(f"❌ Error storing memory in PostgreSQL: {e}")
            import traceback

            traceback.print_exc()
            return None

    def get_memory(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """Get a memory by ID"""
        try:
            with self.get_session() as session:
                memory = session.query(Memory).filter(Memory.id == memory_id).first()
                if memory:
                    return {
                        "id": memory.id,
                        "content": memory.content,
                        "metadata": memory.memory_metadata,
                        "embedding_id": memory.embedding_id,
                        "created_at": memory.created_at,
                        "updated_at": memory.updated_at,
                    }
                return None
        except Exception as e:
            print(f"Error retrieving memory: {e}")
            return None

    def get_memories_by_ids(self, memory_ids: List[int]) -> List[Dict[str, Any]]:
        """Get multiple memories by their IDs (used after Qdrant semantic search)"""
        try:
            with self.get_session() as session:
                memories = session.query(Memory).filter(Memory.id.in_(memory_ids)).all()
                return [
                    {
                        "id": memory.id,
                        "content": memory.content,
                        "metadata": memory.memory_metadata,
                        "embedding_id": memory.embedding_id,
                        "created_at": memory.created_at,
                        "updated_at": memory.updated_at,
                    }
                    for memory in memories
                ]
        except Exception as e:
            print(f"Error retrieving memories: {e}")
            return []

    def update_memory_embedding_id(self, memory_id: int, embedding_id: str) -> bool:
        """Update the embedding ID for a memory (after storing in Qdrant)"""
        try:
            with self.get_session() as session:
                memory = session.query(Memory).filter(Memory.id == memory_id).first()
                if memory:
                    memory.embedding_id = embedding_id
                    memory.updated_at = datetime.utcnow()
                    return True
                return False
        except Exception as e:
            print(f"Error updating memory embedding ID: {e}")
            return False

    # Tool Registry Management (for tool discovery)
    def register_tool(
        self, name: str, description: str, usage: str, tags: Optional[List[str]] = None
    ) -> Optional[int]:
        """
        Register a new tool in the registry.

        Args:
            name: Tool name (must be unique)
            description: Tool description
            usage: How to use the tool
            tags: Optional list of tags for categorization

        Returns:
            Tool ID if successful, None if failed
        """
        try:
            with self.get_session() as session:
                tool = RegisteredTool(
                    name=name, description=description, usage=usage, tags=tags
                )
                session.add(tool)
                session.flush()
                return tool.id
        except Exception as e:
            print(f"Error registering tool: {e}")
            return None

    def get_tool(self, tool_id: int) -> Optional[Dict[str, Any]]:
        """Get a tool by ID"""
        try:
            with self.get_session() as session:
                tool = (
                    session.query(RegisteredTool)
                    .filter(RegisteredTool.id == tool_id)
                    .first()
                )
                if tool:
                    return {
                        "id": tool.id,
                        "name": tool.name,
                        "description": tool.description,
                        "usage": tool.usage,
                        "tags": tool.tags,
                        "created_at": tool.created_at,
                        "updated_at": tool.updated_at,
                    }
                return None
        except Exception as e:
            print(f"Error retrieving tool: {e}")
            return None

    def get_tools_by_context(
        self, query_context: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get tools that match a query context (for tool discovery).
        This is a simple implementation - can be enhanced with better matching logic.
        """
        try:
            with self.get_session() as session:
                # Simple text matching in description and usage fields
                tools = (
                    session.query(RegisteredTool)
                    .filter(
                        (RegisteredTool.description.ilike(f"%{query_context}%"))
                        | (RegisteredTool.usage.ilike(f"%{query_context}%"))
                    )
                    .limit(limit)
                    .all()
                )

                return [
                    {
                        "id": tool.id,
                        "name": tool.name,
                        "description": tool.description,
                        "usage": tool.usage,
                        "tags": tool.tags,
                        "created_at": tool.created_at,
                        "updated_at": tool.updated_at,
                    }
                    for tool in tools
                ]
        except Exception as e:
            print(f"Error retrieving tools by context: {e}")
            return []

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all registered tools"""
        try:
            with self.get_session() as session:
                tools = session.query(RegisteredTool).all()
                return [
                    {
                        "id": tool.id,
                        "name": tool.name,
                        "description": tool.description,
                        "usage": tool.usage,
                        "tags": tool.tags,
                        "created_at": tool.created_at,
                        "updated_at": tool.updated_at,
                    }
                    for tool in tools
                ]
        except Exception as e:
            print(f"Error retrieving all tools: {e}")
            return []


# Global PostgreSQL client instance
postgres_client = PostgresClient()


def get_postgres_client() -> PostgresClient:
    """Get the global PostgreSQL client instance"""
    return postgres_client
