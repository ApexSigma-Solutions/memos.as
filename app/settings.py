"""
Pydantic Settings for memos.as service.
Centralized configuration management using environment variables and Vault.
"""

from typing import Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from apexsigma_core.vault import get_secret


class MemosSettings(BaseSettings):
    """Configuration settings for memos.as service."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database Configuration
    postgres_host: str = Field(default="apexsigma_postgres", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="memos", description="PostgreSQL database name")
    postgres_user: str = Field(default="apexsigma_user", description="PostgreSQL username")
    postgres_password: Optional[str] = Field(default=None, description="PostgreSQL password")
    database_url: Optional[str] = Field(default=None, description="Full database URL")

    # Redis Configuration
    redis_host: str = Field(default="apexsigma_redis", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")

    # Qdrant Vector Database
    qdrant_host: str = Field(default="apexsigma_qdrant", description="Qdrant host")
    qdrant_port: int = Field(default=6333, description="Qdrant port")
    embedding_size: int = Field(default=384, description="Embedding vector size")

    # Neo4j Graph Database
    neo4j_uri: str = Field(default="bolt://apexsigma_neo4j:7687", description="Neo4j URI")
    neo4j_username: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: Optional[str] = Field(default=None, description="Neo4j password")

    # Service Configuration
    memos_base_url: str = Field(default="http://memos-api:8090", description="Memos API base URL")
    api_host: str = Field(default="localhost", description="API host for testing")
    jwt_secret_key: str = Field(default="apexsigma-mcp-secret-key-2025", description="JWT secret key")

    # Memory/Cache TTL Settings
    memory_query_ttl: int = Field(default=1800, description="Memory query TTL in seconds")
    embedding_ttl: int = Field(default=3600, description="Embedding cache TTL in seconds")
    working_memory_ttl: int = Field(default=300, description="Working memory TTL in seconds")
    tool_cache_ttl: int = Field(default=7200, description="Tool cache TTL in seconds")
    llm_response_ttl: int = Field(default=14400, description="LLM response cache TTL in seconds")
    memory_expiration_interval_seconds: int = Field(default=3600, description="Memory expiration check interval")
    apex_namespace: str = Field(default="apex:memos", description="Apex namespace for memory")

    # Observability - Langfuse
    langfuse_host: str = Field(default="https://cloud.langfuse.com", description="Langfuse host URL")
    langfuse_public_key: Optional[str] = Field(default=None, description="Langfuse public key")
    langfuse_secret_key: Optional[str] = Field(default=None, description="Langfuse secret key")

    @field_validator("postgres_password", mode="before")
    @classmethod
    def get_postgres_password(cls, v):
        """Fetch PostgreSQL password from Vault if not provided."""
        if v is None:
            return get_secret("services/memos/database", "postgres_password")
        return v

    @field_validator("redis_password", mode="before")
    @classmethod
    def get_redis_password(cls, v):
        """Fetch Redis password from Vault if not provided."""
        if v is None:
            return get_secret("services/memos/cache", "redis_password")
        return v

    @field_validator("neo4j_password", mode="before")
    @classmethod
    def get_neo4j_password(cls, v):
        """Fetch Neo4j password from Vault if not provided."""
        if v is None:
            return get_secret("services/memos/graph", "neo4j_password")
        return v

    @field_validator("jwt_secret_key", mode="before")
    @classmethod
    def get_jwt_secret_key(cls, v):
        """Fetch JWT secret key from Vault if not provided."""
        if v == "apexsigma-mcp-secret-key-2025":  # Default value
            vault_secret = get_secret("services/memos/security", "jwt_secret_key")
            return vault_secret if vault_secret else v
        return v

    @field_validator("langfuse_public_key", mode="before")
    @classmethod
    def get_langfuse_public_key(cls, v):
        """Fetch Langfuse public key from Vault if not provided."""
        if v is None:
            return get_secret("services/memos/observability", "langfuse_public_key")
        return v

    @field_validator("langfuse_secret_key", mode="before")
    @classmethod
    def get_langfuse_secret_key(cls, v):
        """Fetch Langfuse secret key from Vault if not provided."""
        if v is None:
            return get_secret("services/memos/observability", "langfuse_secret_key")
        return v


# Singleton instance
settings = MemosSettings()
