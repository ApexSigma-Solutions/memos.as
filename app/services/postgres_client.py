import os
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
    Float,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.exc import IntegrityError

Base = declarative_base()


class Memory(Base):
    """
    Core memory table for storing episodic memories with metadata.
    This is the primary storage for the /memory/store endpoint.
    """

    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(Text, nullable=False)
    tier = Column(String(255), nullable=False, default="default")
    memory_metadata = Column(
        JSON, nullable=True
    )  # Renamed from 'metadata' to avoid SQLAlchemy conflict
    embedding_id = Column(String(255), nullable=True)  # Reference to Qdrant vector ID
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


class KnowledgeShareRequestDB(Base):
    __tablename__ = "knowledge_share_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    requester_agent_id = Column(String(255), nullable=False)
    target_agent_id = Column(String(255), nullable=False)
    query = Column(Text, nullable=False)
    confidence_threshold = Column(Float, nullable=False)
    sharing_policy = Column(String(255), nullable=False)
    status = Column(String(255), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


class KnowledgeShareOfferDB(Base):
    __tablename__ = "knowledge_share_offers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    request_id = Column(Integer, nullable=False)
    offering_agent_id = Column(String(255), nullable=False)
    memory_id = Column(Integer, nullable=False)
    confidence_score = Column(Float, nullable=False)
    status = Column(String(255), nullable=False, default="pending")
    created_at = Column(DateTime, default=datetime.utcnow)


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
            self.database = os.environ.get(
                "POSTGRES_DB", "apexsigma_db"
            )  # Updated to canonical default
            self.user = os.environ.get("POSTGRES_USER", "apexsigma_user")
            self.password = os.environ.get(
                "POSTGRES_PASSWORD", "your_secure_postgres_password_here"
            )

            self.database_url = (
                f"postgresql://{self.user}:{self.password}@"
                f"{self.host}:{self.port}/{self.database}"
            )

        # Production-ready connection pooling
        self.engine = create_engine(
            self.database_url,
            echo=False,
            pool_size=10,  # Base connection pool size
            max_overflow=20,  # Maximum overflow connections
            pool_timeout=30,  # Seconds to wait for connection
            pool_recycle=3600,  # Recycle connections after 1 hour
            pool_pre_ping=True,  # Verify connections before use
        )
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
        agent_id: str = "default_agent",
        metadata: Optional[Dict[str, Any]] = None,
        embedding_id: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> Optional[int]:
        """
        Store a new memory entry.

        Args:
            content: The memory content to store
            agent_id: The agent ID to associate with the memory (stored in 'tier' column)
            metadata: Optional metadata dictionary
            embedding_id: Optional reference to Qdrant vector ID

        Returns:
            Memory ID if successful, None if failed
        """
        try:
            with self.get_session() as session:
                # Using the existing 'tier' column to store agent_id to avoid schema migration.
                memory = Memory(
                    content=content,
                    tier=agent_id,
                    memory_metadata=metadata,
                    embedding_id=embedding_id,
                    expires_at=expires_at,
                )
                session.add(memory)
                session.flush()  # Flush to get the ID but don't commit yet
                memory_id = memory.id

                if memory_id is None:
                    print("⚠️  Memory ID is None after flush - database issue")
                    return None

                print(
                    f"✅ Successfully stored memory with ID: {memory_id} for agent {agent_id}"
                )
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
                        "agent_id": memory.tier,  # Using tier column as agent_id
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
                        "agent_id": memory.tier,  # Using tier column as agent_id
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
                try:
                    tool = RegisteredTool(
                        name=name, description=description, usage=usage, tags=tags
                    )
                    session.add(tool)
                    session.flush()
                    return tool.id
                except IntegrityError:
                    session.rollback()
                    existing_tool = (
                        session.query(RegisteredTool)
                        .filter(RegisteredTool.name == name)
                        .first()
                    )
                    if existing_tool:
                        return existing_tool.id
                    raise
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

    def create_knowledge_share_request(
        self,
        requester_agent_id: str,
        target_agent_id: str,
        query: str,
        confidence_threshold: float,
        sharing_policy: str,
    ) -> Optional[int]:
        """Create a new knowledge share request."""
        try:
            with self.get_session() as session:
                request = KnowledgeShareRequestDB(
                    requester_agent_id=requester_agent_id,
                    target_agent_id=target_agent_id,
                    query=query,
                    confidence_threshold=confidence_threshold,
                    sharing_policy=sharing_policy,
                )
                session.add(request)
                session.flush()
                return request.id
        except Exception as e:
            print(f"Error creating knowledge share request: {e}")
            return None

    def create_knowledge_share_offer(
        self,
        request_id: int,
        offering_agent_id: str,
        memory_id: int,
        confidence_score: float,
    ) -> Optional[int]:
        """Create a new knowledge share offer."""
        try:
            with self.get_session() as session:
                offer = KnowledgeShareOfferDB(
                    request_id=request_id,
                    offering_agent_id=offering_agent_id,
                    memory_id=memory_id,
                    confidence_score=confidence_score,
                )
                session.add(offer)
                session.flush()
                return offer.id
        except Exception as e:
            print(f"Error creating knowledge share offer: {e}")
            return None

    def get_pending_knowledge_share_requests(
        self, agent_id: str
    ) -> List[Dict[str, Any]]:
        """Get pending knowledge share requests for a given agent."""
        try:
            with self.get_session() as session:
                requests = (
                    session.query(KnowledgeShareRequestDB)
                    .filter(
                        KnowledgeShareRequestDB.target_agent_id == agent_id,
                        KnowledgeShareRequestDB.status == "pending",
                    )
                    .all()
                )
                return [
                    {
                        "id": request.id,
                        "requester_agent_id": request.requester_agent_id,
                        "target_agent_id": request.target_agent_id,
                        "query": request.query,
                        "confidence_threshold": request.confidence_threshold,
                        "sharing_policy": request.sharing_policy,
                        "status": request.status,
                        "created_at": request.created_at,
                    }
                    for request in requests
                ]
        except Exception as e:
            print(f"Error getting pending knowledge share requests: {e}")
            return []

    def get_knowledge_share_request_by_id(
        self, request_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get a knowledge share request by its ID."""
        try:
            with self.get_session() as session:
                request = (
                    session.query(KnowledgeShareRequestDB)
                    .filter(KnowledgeShareRequestDB.id == request_id)
                    .first()
                )
                if request:
                    return {
                        "id": request.id,
                        "requester_agent_id": request.requester_agent_id,
                        "target_agent_id": request.target_agent_id,
                        "query": request.query,
                        "confidence_threshold": request.confidence_threshold,
                        "sharing_policy": request.sharing_policy,
                        "status": request.status,
                        "created_at": request.created_at,
                    }
                return None
        except Exception as e:
            print(f"Error getting knowledge share request by id: {e}")
            return None


# Global PostgreSQL client instance (lazy-initialized to avoid import-time side effects)
_postgres_client: Optional[PostgresClient] = None


def get_postgres_client() -> PostgresClient:
    """Return a lazily-instantiated global PostgresClient.

    This avoids creating a DB engine (and importing DB drivers) at module
    import time, which prevents tools like Alembic from importing the
    SQLAlchemy "Base" metadata for autogeneration.
    """
    global _postgres_client
    if _postgres_client is None:
        _postgres_client = PostgresClient()
    return _postgres_client


# Backwards-compatible alias: some modules/tests may import `postgres_client`.
# Importers should prefer `get_postgres_client()` but we provide a property-like
# attribute that resolves to the live client when accessed.
class _LazyPostgresClientProxy:
    def __getattr__(self, item: str):
        return getattr(get_postgres_client(), item)


postgres_client = _LazyPostgresClientProxy()
