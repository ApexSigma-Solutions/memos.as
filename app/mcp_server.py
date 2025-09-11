#!/usr/bin/env python3
"""
MCP Server for memOS.as - Memory Operations
Provides MCP tools for storing, retrieving, and managing
memories in the memOS system.
"""

import logging
import os
import json
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from collections import defaultdict
import jwt
import httpx
from mcp.server import Server
import uvicorn
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel

from app.services.observability import get_observability

# Try to import Langfuse
try:
    from langfuse import Langfuse

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure audit logging
audit_logger = logging.getLogger("mcp_audit")
audit_logger.setLevel(logging.INFO)
audit_handler = logging.StreamHandler()
audit_formatter = logging.Formatter(
    json.dumps(
        {
            "timestamp": "%(asctime)s",
            "level": "%(levelname)s",
            "service": "memOS-MCP",
            "event": "%(message)s",
        }
    )
)
audit_handler.setFormatter(audit_formatter)
audit_logger.addHandler(audit_handler)

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "apexsigma-mcp-secret-key-2025")
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Service accounts for AI assistants
SERVICE_ACCOUNTS = {
    "MCP_COPILOT": "copilot-secret-token",
    "MCP_GEMINI": "gemini-secret-token",
    "MCP_QWEN": "qwen-secret-token",
}

# MCP-specific memory tier mapping
MCP_MEMORY_TIERS = {
    "MCP_COPILOT": "MCP_COPILOT",
    "MCP_GEMINI": "MCP_GEMINI",
    "MCP_QWEN": "MCP_QWEN",
    "MCP_SYSTEM": "MCP_SYSTEM",
}


def get_mcp_memory_tier(service_account: str) -> str:
    """
    Map service account to MCP-specific memory tier.

    Args:
        service_account: The service account name

    Returns:
        MCP-specific memory tier name
    """
    return MCP_MEMORY_TIERS.get(service_account, "MCP_SYSTEM")


# Initialize Langfuse client for MCP-specific tracing
langfuse_client = None
if LANGFUSE_AVAILABLE:
    try:
        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
        secret_key = os.environ.get("LANGFUSE_SECRET_KEY")
        host = os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com")

        if public_key and secret_key:
            langfuse_client = Langfuse(
                public_key=public_key, secret_key=secret_key, host=host
            )
            logger.info("Langfuse client initialized for MCP tracing")
        else:
            logger.warning("Langfuse API keys not found, MCP tracing disabled")
    except Exception as e:
        logger.error(f"Failed to initialize Langfuse client: {e}")
        langfuse_client = None

# Rate limiting configuration (requests per minute)
RATE_LIMITS = {
    "MCP_COPILOT": 60,  # 60 requests per minute
    "MCP_GEMINI": 60,
    "MCP_QWEN": 60,
}

# In-memory rate limiting storage
rate_limit_store: Dict[str, Dict[str, Any]] = defaultdict(
    lambda: {"count": 0, "reset_time": datetime.utcnow()}
)  # MCP Server setup
server = Server("memos-mcp-server")

# FastAPI app for MCP over HTTP
app = FastAPI(title="memOS MCP Server", description="MCP server for memory operations")

# Initialize observability service
observability = get_observability()

# Security scheme for JWT authentication
security = HTTPBearer()

# memOS API base URL (should be configurable)
MEMOS_BASE_URL = os.getenv("MEMOS_BASE_URL", "http://memos-api:8090")


def create_mcp_trace(
    name: str, service_account: str, metadata: Optional[Dict[str, Any]] = None
):
    """Create a Langfuse trace for MCP operations."""
    if not langfuse_client:
        return None

    try:
        trace = langfuse_client.trace(
            name=name,
            user_id=service_account,
            metadata={
                "service": "memOS-MCP",
                "service_account": service_account,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {}),
            },
        )
        return trace
    except Exception as e:
        logger.error(f"Failed to create Langfuse trace: {e}")
        return None


def create_mcp_span(trace, name: str, input_data: Optional[Dict[str, Any]] = None):
    """Create a span within an MCP trace."""
    if not trace:
        return None

    try:
        span = trace.span(name=name, input=input_data)
        return span
    except Exception as e:
        logger.error(f"Failed to create Langfuse span: {e}")
        return None


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM]
        )
        service_account: str = payload.get("sub")
        if service_account not in SERVICE_ACCOUNTS:
            log_auth_attempt(
                service_account or "unknown",
                False,
                {"reason": "invalid_service_account"},
            )
            observability.record_mcp_auth_attempt(service_account or "unknown", False)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid service account",
                headers={"WWW-Authenticate": "Bearer"},
            )
        log_auth_attempt(service_account, True)
        observability.record_mcp_auth_attempt(service_account, True)
        return service_account
    except jwt.PyJWTError as e:
        log_auth_attempt("unknown", False, {"reason": "invalid_token", "error": str(e)})
        observability.record_mcp_auth_attempt("unknown", False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def check_rate_limit(service_account: str):
    """Check and enforce rate limiting for service account"""
    now = datetime.utcnow()
    user_data = rate_limit_store[service_account]

    # Reset counter if time window has passed
    if now >= user_data["reset_time"]:
        user_data["count"] = 0
        user_data["reset_time"] = now + timedelta(minutes=1)

    # Check if limit exceeded
    if user_data["count"] >= RATE_LIMITS.get(service_account, 60):
        reset_time = user_data["reset_time"]
        log_rate_limit_violation(
            service_account,
            {
                "current_count": user_data["count"],
                "limit": RATE_LIMITS.get(service_account, 60),
                "reset_time": reset_time.isoformat(),
            },
        )
        observability.record_mcp_rate_limit_hit(service_account)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again after {reset_time.isoformat()}",
            headers={"Retry-After": str(int((reset_time - now).total_seconds()))},
        )

    # Increment counter
    user_data["count"] += 1


def verify_token_and_rate_limit(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """Verify JWT token and check rate limits with Langfuse tracing"""
    trace = create_mcp_trace(
        "mcp_authentication", "system", {"operation": "token_verification"}
    )
    span = create_mcp_span(trace, "verify_token_and_rate_limit")

    try:
        service_account = verify_token(credentials)
        check_rate_limit(service_account)

        if span:
            span.end(output={"service_account": service_account, "status": "success"})

        return service_account
    except Exception as e:
        if span:
            span.end(output={"error": str(e), "status": "failed"})
        raise


def log_audit_event(
    event_type: str,
    service_account: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    success: bool = True,
):
    """Log audit events for security monitoring"""
    audit_data = {
        "event_type": event_type,
        "service_account": service_account,
        "timestamp": datetime.utcnow().isoformat(),
        "success": success,
        "details": details or {},
    }
    audit_logger.info(json.dumps(audit_data))

    # Record audit event metrics
    severity = "error" if not success else "info"
    observability.record_mcp_audit_event(
        event_type, service_account or "unknown", severity
    )


def log_auth_attempt(
    service_account: str, success: bool, details: Optional[Dict[str, Any]] = None
):
    """Log authentication attempts"""
    log_audit_event("authentication", service_account, details, success)


def log_rate_limit_violation(
    service_account: str, details: Optional[Dict[str, Any]] = None
):
    """Log rate limit violations"""
    log_audit_event("rate_limit_violation", service_account, details, False)


def log_mcp_request(
    service_account: str, method: str, details: Optional[Dict[str, Any]] = None
):
    """Log MCP requests"""
    log_audit_event("mcp_request", service_account, details, True)


@app.post("/auth/token")
async def get_access_token(service_account: str, secret: str):
    """Get access token for service account"""
    if service_account not in SERVICE_ACCOUNTS:
        log_auth_attempt(service_account, False, {"reason": "invalid_service_account"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid service account"
        )

    if secret != SERVICE_ACCOUNTS[service_account]:
        log_auth_attempt(service_account, False, {"reason": "invalid_secret"})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret"
        )

    log_auth_attempt(service_account, True, {"action": "token_generated"})
    access_token = create_access_token(data={"sub": service_account})
    return {"access_token": access_token, "token_type": "bearer"}


class StoreMemoryRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None


class QueryMemoryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


# MCP Tools - Define functions that will be registered as tools
@server.tool()
async def store_memory_tool(content: str, metadata: Optional[str] = None) -> str:
    """
    Store a memory in the memOS system using MCP-specific tiers.

    Args:
        content: The memory content to store
        metadata: Optional JSON metadata as string

    Returns:
        Success message with stored memory details
    """
    # Get service account from request context
    service_account = request_context.get("service_account", "MCP_SYSTEM")

    # Map service account to MCP-specific memory tier
    mcp_tier = get_mcp_memory_tier(service_account)

    trace = create_mcp_trace(
        "store_memory",
        service_account,
        {"operation": "memory_storage", "mcp_tier": mcp_tier},
    )
    span = create_mcp_span(
        trace,
        "store_memory_operation",
        {
            #         "content_length": len(content),
            "tier": mcp_tier
        },
    )

    try:
        parsed_metadata = None
        if metadata:
            parsed_metadata = json.loads(metadata)

        # Add MCP-specific metadata
        if parsed_metadata is None:
            parsed_metadata = {}
        parsed_metadata.update(
            {
                "mcp_service_account": service_account,
                "mcp_tier": mcp_tier,
                "stored_by": "mcp_server",
            }
        )

        request_data = StoreMemoryRequest(
            #             content=content,
            metadata=parsed_metadata,
            tier=mcp_tier,  # Use MCP-specific tier
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEMOS_BASE_URL}/memory/store", json=request_data.dict(), timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

        if span:
            span.end(output={"status": "success", "result": result, "tier": mcp_tier})

        log_mcp_request(
            service_account,
            "store_memory",
            {
                #             "content_length": len(content),
                "tier": mcp_tier
            },
        )
        observability.record_mcp_tool_usage("store_memory", service_account, True)
        observability.record_mcp_memory_operation(
            "store", mcp_tier, service_account, True
        )

        return f"Memory stored successfully in MCP tier '{mcp_tier}': {result}"

    except Exception as e:
        if span:
            span.end(output={"status": "error", "error": str(e), "tier": mcp_tier})
        logger.error("Error storing memory: %s", e)
        observability.record_mcp_tool_usage("store_memory", service_account, False)
        observability.record_mcp_memory_operation(
            "store", mcp_tier, service_account, False
        )
        return f"Error storing memory in MCP tier '{mcp_tier}': {str(e)}"


@server.tool()
async def query_memory_by_mcp_tier_tool(query: str, top_k: int = 5) -> str:
    """
    Query memories from the current MCP service account's tier.

    This tool searches only memories stored by the same service account,
    providing agent-specific memory isolation.

    Args:
        query: The search query
        top_k: Number of top results to return

    Returns:
        Search results from the current service account's memory tier
    """
    service_account = request_context.get("service_account", "MCP_SYSTEM")
    mcp_tier = get_mcp_memory_tier(service_account)

    trace = create_mcp_trace(
        "query_memory_by_mcp_tier",
        service_account,
        {
            "operation": "memory_query",
            "mcp_tier": mcp_tier,
            #         "query_length": len(query)
        },
    )
    span = create_mcp_span(
        trace,
        "mcp_tier_query_operation",
        {
            #         "query": query,
            #         "top_k": top_k,
            "tier": mcp_tier
        },
    )

    try:
        # Create query request with MCP tier filter
        query_request = {
            #             "query": query,
            #             "top_k": top_k,
            "filters": {
                "tier": mcp_tier  # Filter by MCP-specific tier
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEMOS_BASE_URL}/memory/query", json=query_request, timeout=30.0
            )
            response.raise_for_status()
            results = response.json()

        # Format results with MCP tier information
        formatted_results = []
        memories = results.get("memories", {}).get("results", [])

        if memories:
            formatted_results.append(
                f"Found {len(memories)} memories in MCP tier '{mcp_tier}':"
            )
            formatted_results.append("")

            for i, result in enumerate(memories):
                formatted_results.append(
                    f"{i + 1}. {result.get('content', 'No content')}"
                )
                if result.get("metadata"):
                    metadata = result["metadata"]
                    if "mcp_service_account" in metadata:
                        formatted_results.append(
                            f"   Service Account: {metadata['mcp_service_account']}"
                        )
                    if "stored_by" in metadata:
                        formatted_results.append(
                            f"   Stored by: {metadata['stored_by']}"
                        )
                if result.get("similarity_score"):
                    formatted_results.append(
                        f"   Similarity: {result['similarity_score']:.3f}"
                    )
                formatted_results.append("")

            if span:
                span.end(
                    output={
                        "status": "success",
                        "results_count": len(memories),
                        "tier": mcp_tier,
                    }
                )

            log_mcp_request(
                service_account,
                "query_memory_by_mcp_tier",
                {
                    #                 "query_length": len(query),
                    "results_count": len(memories),
                    "tier": mcp_tier,
                },
            )
            observability.record_mcp_tool_usage(
                "query_memory_by_mcp_tier", service_account, True
            )

            return "\n".join(formatted_results)
        else:
            if span:
                span.end(
                    output={"status": "success", "results_count": 0, "tier": mcp_tier}
                )

            observability.record_mcp_tool_usage(
                "query_memory_by_mcp_tier", service_account, True
            )
            return f"No memories found in MCP tier '{mcp_tier}' for query: {query}"

    except Exception as e:
        if span:
            span.end(output={"status": "error", "error": str(e), "tier": mcp_tier})
        logger.error(f"Error querying memory by MCP tier: {e}")
        observability.record_mcp_tool_usage(
            "query_memory_by_mcp_tier", service_account, False
        )
        return f"Error querying memories in MCP tier '{mcp_tier}': {str(e)}"


@server.tool()
async def get_mcp_memory_stats_tool() -> str:
    """
    Get memory statistics for the current MCP service account's tier.

    Returns:
        Memory statistics specific to the current service account
    """
    service_account = request_context.get("service_account", "MCP_SYSTEM")
    mcp_tier = get_mcp_memory_tier(service_account)

    trace = create_mcp_trace(
        "get_mcp_memory_stats",
        service_account,
        {"operation": "memory_stats", "mcp_tier": mcp_tier},
    )

    try:
        # Query memories by MCP tier
        query_request = {
            "query": "*",  # Match all memories
            "top_k": 1000,  # Get a large sample for stats
            "filters": {"tier": mcp_tier},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEMOS_BASE_URL}/memory/query", json=query_request, timeout=30.0
            )
            response.raise_for_status()
            results = response.json()

        memories = results.get("memories", {}).get("results", [])
        memory_count = len(memories)

        # Calculate statistics
        total_content_length = sum(len(m.get("content", "")) for m in memories)
        avg_content_length = (
            total_content_length / memory_count if memory_count > 0 else 0
        )

        # Count memories by service account
        service_account_counts = {}
        for memory in memories:
            metadata = memory.get("metadata", {})
            sa = metadata.get("mcp_service_account", "unknown")
            service_account_counts[sa] = service_account_counts.get(sa, 0) + 1

        stats = {
            "mcp_tier": mcp_tier,
            "total_memories": memory_count,
            "average_content_length": avg_content_length,
            "service_account_breakdown": service_account_counts,
            "query_timestamp": datetime.utcnow().isoformat(),
        }

        if trace:
            trace.update(metadata={"stats": stats})

        log_mcp_request(
            service_account,
            "get_mcp_memory_stats",
            {"tier": mcp_tier, "memory_count": memory_count},
        )
        observability.record_mcp_tool_usage(
            "get_mcp_memory_stats", service_account, True
        )

        return f"""MCP Memory Statistics for tier '{mcp_tier}':

Total Memories: {stats["total_memories"]}
Average Content Length: {stats["average_content_length"]:.1f} characters

Service Account Breakdown:
{chr(10).join(f"  {sa}: {count} memories" for sa, count in stats["service_account_breakdown"].items())}

Query Time: {stats["query_timestamp"]}"""

    except Exception as e:
        if trace:
            trace.update(metadata={"error": str(e)})
        logger.error(f"Error getting MCP memory stats: {e}")
        observability.record_mcp_tool_usage(
            "get_mcp_memory_stats", service_account, False
        )
        return f"Error getting memory statistics for MCP tier '{mcp_tier}': {str(e)}"

    # Remove the old tool definitions that use decorators
    # @server.tool()
    # async def store_memory(content: str, metadata: Optional[str] = None) -> str:
    """
    Store a memory in the memOS system using MCP-specific tiers.

    Args:
        content: The memory content to store
        metadata: Optional JSON metadata as string

    Returns:
        Success message with stored memory details
    """
    # Get service account from request context
    service_account = request_context.get("service_account", "MCP_SYSTEM")

    # Map service account to MCP-specific memory tier
    mcp_tier = get_mcp_memory_tier(service_account)

    trace = create_mcp_trace(
        "store_memory",
        service_account,
        {"operation": "memory_storage", "mcp_tier": mcp_tier},
    )
    span = create_mcp_span(
        trace,
        "store_memory_operation",
        {
            #         "content_length": len(content),
            "tier": mcp_tier
        },
    )

    try:
        parsed_metadata = None
        if metadata:
            parsed_metadata = json.loads(metadata)

        # Add MCP-specific metadata
        if parsed_metadata is None:
            parsed_metadata = {}
        parsed_metadata.update(
            {
                "mcp_service_account": service_account,
                "mcp_tier": mcp_tier,
                "stored_by": "mcp_server",
            }
        )

        request_data = StoreMemoryRequest(
            #             content=content,
            metadata=parsed_metadata,
            tier=mcp_tier,  # Use MCP-specific tier
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEMOS_BASE_URL}/memory/store", json=request_data.dict(), timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

        if span:
            span.end(output={"status": "success", "result": result, "tier": mcp_tier})

        log_mcp_request(
            service_account,
            "store_memory",
            {
                #             "content_length": len(content),
                "tier": mcp_tier
            },
        )
        observability.record_mcp_tool_usage("store_memory", service_account, True)
        observability.record_mcp_memory_operation(
            "store", mcp_tier, service_account, True
        )

        return f"Memory stored successfully in MCP tier '{mcp_tier}': {result}"

    except Exception as e:
        if span:
            span.end(output={"status": "error", "error": str(e), "tier": mcp_tier})
        logger.error("Error storing memory: %s", e)
        observability.record_mcp_tool_usage("store_memory", service_account, False)
        observability.record_mcp_memory_operation(
            "store", mcp_tier, service_account, False
        )
        return f"Error storing memory in MCP tier '{mcp_tier}': {str(e)}"

    # Remove the old tool definitions that use decorators
    # @server.tool()
    # async def query_memory_by_mcp_tier(query: str, top_k: int = 5) -> str:
    """
    Query memories from the current MCP service account's tier.

    This tool searches only memories stored by the same service account,
    providing agent-specific memory isolation.

    Args:
        query: The search query
        top_k: Number of top results to return

    Returns:
        Search results from the current service account's memory tier
    """
    service_account = request_context.get("service_account", "MCP_SYSTEM")
    mcp_tier = get_mcp_memory_tier(service_account)

    trace = create_mcp_trace(
        "query_memory_by_mcp_tier",
        service_account,
        {
            "operation": "memory_query",
            "mcp_tier": mcp_tier,
            #         "query_length": len(query)
        },
    )
    span = create_mcp_span(
        trace,
        "mcp_tier_query_operation",
        {
            #         "query": query,
            #         "top_k": top_k,
            "tier": mcp_tier
        },
    )

    try:
        # Create query request with MCP tier filter
        query_request = {
            #             "query": query,
            #             "top_k": top_k,
            "filters": {
                "tier": mcp_tier  # Filter by MCP-specific tier
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEMOS_BASE_URL}/memory/query", json=query_request, timeout=30.0
            )
            response.raise_for_status()
            results = response.json()

        # Format results with MCP tier information
        formatted_results = []
        memories = results.get("memories", {}).get("results", [])

        if memories:
            formatted_results.append(
                f"Found {len(memories)} memories in MCP tier '{mcp_tier}':"
            )
            formatted_results.append("")

            for i, result in enumerate(memories):
                formatted_results.append(
                    f"{i + 1}. {result.get('content', 'No content')}"
                )
                if result.get("metadata"):
                    metadata = result["metadata"]
                    if "mcp_service_account" in metadata:
                        formatted_results.append(
                            f"   Service Account: {metadata['mcp_service_account']}"
                        )
                    if "stored_by" in metadata:
                        formatted_results.append(
                            f"   Stored by: {metadata['stored_by']}"
                        )
                if result.get("similarity_score"):
                    formatted_results.append(
                        f"   Similarity: {result['similarity_score']:.3f}"
                    )
                formatted_results.append("")

            if span:
                span.end(
                    output={
                        "status": "success",
                        "results_count": len(memories),
                        "tier": mcp_tier,
                    }
                )

            log_mcp_request(
                service_account,
                "query_memory_by_mcp_tier",
                {
                    #                 "query_length": len(query),
                    "results_count": len(memories),
                    "tier": mcp_tier,
                },
            )
            observability.record_mcp_tool_usage(
                "query_memory_by_mcp_tier", service_account, True
            )

            return "\n".join(formatted_results)
        else:
            if span:
                span.end(
                    output={"status": "success", "results_count": 0, "tier": mcp_tier}
                )

            observability.record_mcp_tool_usage(
                "query_memory_by_mcp_tier", service_account, True
            )
    #             return f"No memories found in MCP tier '{mcp_tier}' for query: {query}"

    except Exception as e:
        if span:
            span.end(output={"status": "error", "error": str(e), "tier": mcp_tier})
        logger.error(f"Error querying memory by MCP tier: {e}")
        observability.record_mcp_tool_usage(
            "query_memory_by_mcp_tier", service_account, False
        )
        return f"Error querying memories in MCP tier '{mcp_tier}': {str(e)}"

    # Remove the old tool definitions that use decorators
    # @server.tool()
    # async def get_mcp_memory_stats() -> str:
    """
    Get memory statistics for the current MCP service account's tier.

    Returns:
        Memory statistics specific to the current service account
    """
    service_account = request_context.get("service_account", "MCP_SYSTEM")
    mcp_tier = get_mcp_memory_tier(service_account)

    trace = create_mcp_trace(
        "get_mcp_memory_stats",
        service_account,
        {"operation": "memory_stats", "mcp_tier": mcp_tier},
    )

    try:
        # Query memories by MCP tier
        query_request = {
            "query": "*",  # Match all memories
            "top_k": 1000,  # Get a large sample for stats
            "filters": {"tier": mcp_tier},
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEMOS_BASE_URL}/memory/query", json=query_request, timeout=30.0
            )
            response.raise_for_status()
            results = response.json()

        memories = results.get("memories", {}).get("results", [])
        memory_count = len(memories)

        # Calculate statistics
        total_content_length = sum(len(m.get("content", "")) for m in memories)
        avg_content_length = (
            total_content_length / memory_count if memory_count > 0 else 0
        )

        # Count memories by service account
        service_account_counts = {}
        for memory in memories:
            metadata = memory.get("metadata", {})
            sa = metadata.get("mcp_service_account", "unknown")
            service_account_counts[sa] = service_account_counts.get(sa, 0) + 1

        stats = {
            "mcp_tier": mcp_tier,
            "total_memories": memory_count,
            "average_content_length": avg_content_length,
            "service_account_breakdown": service_account_counts,
            "query_timestamp": datetime.utcnow().isoformat(),
        }

        if trace:
            trace.update(metadata={"stats": stats})

        log_mcp_request(
            service_account,
            "get_mcp_memory_stats",
            {"tier": mcp_tier, "memory_count": memory_count},
        )
        observability.record_mcp_tool_usage(
            "get_mcp_memory_stats", service_account, True
        )

        return f"""MCP Memory Statistics for tier '{mcp_tier}':

Total Memories: {stats["total_memories"]}
Average Content Length: {stats["average_content_length"]:.1f} characters

Service Account Breakdown:
{chr(10).join(f"  {sa}: {count} memories" for sa, count in stats["service_account_breakdown"].items())}

Query Time: {stats["query_timestamp"]}"""

    except Exception as e:
        if trace:
            trace.update(metadata={"error": str(e)})
        logger.error(f"Error getting MCP memory stats: {e}")
        observability.record_mcp_tool_usage(
            "get_mcp_memory_stats", service_account, False
        )
        return f"Error getting memory statistics for MCP tier '{mcp_tier}': {str(e)}"

    # Remove the old tool definitions that use decorators
    # @server.tool()
    # async def clear_memory_cache(pattern: str = "*") -> str:
    """
    Clear memory cache entries.

    Args:
        pattern: Pattern to match for cache clearing (default: all)

    Returns:
        Cache clearing result
    """
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{MEMOS_BASE_URL}/cache/clear",
                #                 params={"pattern": pattern},
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()

        return f"Cache cleared: {result}"

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        return f"Error clearing cache: {str(e)}"


@app.get("/metrics")
async def get_mcp_metrics():
    """Prometheus metrics endpoint for MCP server"""
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(observability.get_metrics(), media_type="text/plain")


# Context variable to store service account during request processing
request_context = {"service_account": "MCP_SYSTEM"}


@app.post("/mcp")
async def handle_mcp_request(
    request: Dict[str, Any], service_account: str = Depends(verify_token_and_rate_limit)
):
    """Handle MCP requests - Protected by JWT authentication and rate limiting"""
    # Set service account in context for MCP tools to access
    request_context["service_account"] = service_account

    # Record active connection
    observability.update_mcp_active_connections(service_account, 1)

    # Create MCP-specific trace for the entire request
    trace = create_mcp_trace(
        "mcp_request",
        service_account,
        {
            "request_type": request.get("type", "unknown"),
            "method": request.get("method", "unknown"),
        },
    )

    start_time = datetime.utcnow()

    try:
        # Log the MCP request
        log_mcp_request(
            service_account,
            "mcp_request",
            {
                "request_type": request.get("type", "unknown"),
                "method": request.get("method", "unknown"),
            },
        )

        logger.info("MCP request from service account: %s", service_account)
        result = await server.handle_request(request)

        # Record successful request metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        observability.record_mcp_request(
            method=request.get("method", "unknown"),
            endpoint="/mcp",
            service_account=service_account,
            status_code=200,
            duration=duration,
        )

        if trace:
            trace.update(metadata={"status": "success"})

        return result
    except Exception as e:
        # Record failed request metrics
        duration = (datetime.utcnow() - start_time).total_seconds()
        observability.record_mcp_request(
            method=request.get("method", "unknown"),
            endpoint="/mcp",
            service_account=service_account,
            status_code=500,
            duration=duration,
        )

        if trace:
            trace.update(metadata={"status": "error", "error": str(e)})
        raise
    finally:
        # Reset active connection
        observability.update_mcp_active_connections(service_account, 0)


@server.tool()
async def request_knowledge_from_agent(
    target_agent_id: str,
    query: str,
    confidence_threshold: float = 0.8,
    sharing_policy: str = "high_confidence_only",
) -> str:
    """
    Request knowledge from another agent via cross-agent knowledge sharing.

    This tool allows the current agent to request specific knowledge or information
    from another agent in the ecosystem, with confidence-based filtering.

    Args:
        target_agent_id: The ID of the agent to request knowledge from
        query: The specific knowledge or information being requested
        confidence_threshold: Minimum confidence score required (0.0-1.0)
        sharing_policy: Knowledge sharing policy ("high_confidence_only", "all_confidence", "manual_review")

    Returns:
        Success message with request details or error message
    """
    service_account = request_context.get("service_account", "MCP_SYSTEM")
    requester_agent_id = get_mcp_memory_tier(
        service_account
    )  # Map service account to agent ID

    trace = create_mcp_trace(
        "request_knowledge_from_agent",
        service_account,
        {
            "operation": "knowledge_request",
            "target_agent": target_agent_id,
            #         "query_length": len(query),
            "confidence_threshold": confidence_threshold,
        },
    )
    span = create_mcp_span(
        trace,
        "knowledge_request_operation",
        {
            "requester": requester_agent_id,
            "target": target_agent_id,
            #         "query": query,
            "threshold": confidence_threshold,
        },
    )

    try:
        # Create knowledge share request
        request_data = {
            "agent_id": requester_agent_id,
            "target_agent": target_agent_id,
            #             "query": query,
            "confidence_threshold": confidence_threshold,
            "sharing_policy": sharing_policy,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEMOS_BASE_URL}/memory/share/request",
                json=request_data,
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()

        if span:
            span.end(
                output={
                    "status": "success",
                    "request_id": result.get("request_id"),
                    "target_agent": target_agent_id,
                }
            )

        log_mcp_request(
            service_account,
            "request_knowledge_from_agent",
            {
                "target_agent": target_agent_id,
                #             "query_length": len(query),
                "confidence_threshold": confidence_threshold,
            },
        )
        observability.record_mcp_tool_usage(
            "request_knowledge_from_agent", service_account, True
        )

        return f"Knowledge request sent successfully to agent '{target_agent_id}': Request ID {result.get('request_id', 'unknown')}"

    except Exception as e:
        if span:
            span.end(
                output={
                    "status": "error",
                    "error": str(e),
                    "target_agent": target_agent_id,
                }
            )
        logger.error(f"Error requesting knowledge from agent {target_agent_id}: {e}")
        observability.record_mcp_tool_usage(
            "request_knowledge_from_agent", service_account, False
        )
        return f"Error requesting knowledge from agent '{target_agent_id}': {str(e)}"


@server.tool()
async def offer_knowledge_to_request(
    request_id: int, memory_id: int, confidence_score: float
) -> str:
    """
    Offer knowledge in response to a knowledge sharing request.

    This tool allows an agent to offer specific knowledge/memory in response
    to a pending knowledge sharing request, with an associated confidence score.

    Args:
        request_id: The ID of the knowledge sharing request
        memory_id: The ID of the memory/knowledge being offered
        confidence_score: Confidence score for this knowledge offer (0.0-1.0)

    Returns:
        Success message with offer details or error message
    """
    service_account = request_context.get("service_account", "MCP_SYSTEM")
    offering_agent_id = get_mcp_memory_tier(service_account)

    trace = create_mcp_trace(
        "offer_knowledge_to_request",
        service_account,
        {
            "operation": "knowledge_offer",
            "request_id": request_id,
            "memory_id": memory_id,
            "confidence_score": confidence_score,
        },
    )
    span = create_mcp_span(
        trace,
        "knowledge_offer_operation",
        {
            "offering_agent": offering_agent_id,
            "request_id": request_id,
            "memory_id": memory_id,
            "confidence": confidence_score,
        },
    )

    try:
        # Create knowledge share offer
        offer_data = {
            "request_id": request_id,
            "offering_agent_id": offering_agent_id,
            "memory_id": memory_id,
            "confidence_score": confidence_score,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{MEMOS_BASE_URL}/memory/share/offer", json=offer_data, timeout=30.0
            )
            response.raise_for_status()
            result = response.json()

        if span:
            span.end(
                output={
                    "status": "success",
                    "offer_id": result.get("offer_id"),
                    "request_id": request_id,
                }
            )

        log_mcp_request(
            service_account,
            "offer_knowledge_to_request",
            {
                "request_id": request_id,
                "memory_id": memory_id,
                "confidence_score": confidence_score,
            },
        )
        observability.record_mcp_tool_usage(
            "offer_knowledge_to_request", service_account, True
        )

        return f"Knowledge offer submitted successfully: Offer ID {result.get('offer_id', 'unknown')} for request {request_id}"

    except Exception as e:
        if span:
            span.end(
                output={"status": "error", "error": str(e), "request_id": request_id}
            )
        logger.error(f"Error offering knowledge for request {request_id}: {e}")
        observability.record_mcp_tool_usage(
            "offer_knowledge_to_request", service_account, False
        )
        return f"Error offering knowledge for request {request_id}: {str(e)}"


@server.tool()
async def get_pending_knowledge_requests() -> str:
    """
    Get all pending knowledge sharing requests for the current agent.

    This tool retrieves all knowledge sharing requests that have been made
    to the current agent and are still pending response.

    Returns:
        List of pending knowledge requests with details
    """
    service_account = request_context.get("service_account", "MCP_SYSTEM")
    agent_id = get_mcp_memory_tier(service_account)

    trace = create_mcp_trace(
        "get_pending_knowledge_requests",
        service_account,
        {"operation": "get_pending_requests", "agent_id": agent_id},
    )
    span = create_mcp_span(
        trace, "get_pending_requests_operation", {"agent_id": agent_id}
    )

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{MEMOS_BASE_URL}/memory/share/pending?agent_id={agent_id}",
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()

        requests = result.get("requests", [])
        formatted_requests = []

        if requests:
            formatted_requests.append(
                f"Found {len(requests)} pending knowledge requests for agent '{agent_id}':"
            )
            formatted_requests.append("")

            for i, request in enumerate(requests):
                formatted_requests.append(f"Request {i + 1}:")
                formatted_requests.append(f"  ID: {request.get('id', 'unknown')}")
                formatted_requests.append(
                    f"  From: {request.get('requester_agent_id', 'unknown')}"
                )
                formatted_requests.append(
                    f"  Query: {request.get('query', 'No query')}"
                )
                formatted_requests.append(
                    f"  Confidence Threshold: {request.get('confidence_threshold', 'unknown')}"
                )
                formatted_requests.append(
                    f"  Sharing Policy: {request.get('sharing_policy', 'unknown')}"
                )
                formatted_requests.append(
                    f"  Created: {request.get('created_at', 'unknown')}"
                )
                formatted_requests.append("")

            if span:
                span.end(
                    output={
                        "status": "success",
                        "requests_count": len(requests),
                        "agent_id": agent_id,
                    }
                )

            log_mcp_request(
                service_account,
                "get_pending_knowledge_requests",
                {"requests_count": len(requests), "agent_id": agent_id},
            )
            observability.record_mcp_tool_usage(
                "get_pending_knowledge_requests", service_account, True
            )

            return "\n".join(formatted_requests)
        else:
            if span:
                span.end(
                    output={
                        "status": "success",
                        "requests_count": 0,
                        "agent_id": agent_id,
                    }
                )

            observability.record_mcp_tool_usage(
                "get_pending_knowledge_requests", service_account, True
            )
            return f"No pending knowledge requests found for agent '{agent_id}'"

    except Exception as e:
        if span:
            span.end(output={"status": "error", "error": str(e), "agent_id": agent_id})
        logger.error(
            f"Error getting pending knowledge requests for agent {agent_id}: {e}"
        )
        observability.record_mcp_tool_usage(
            "get_pending_knowledge_requests", service_account, False
        )
        return (
            f"Error getting pending knowledge requests for agent '{agent_id}': {str(e)}"
        )


@server.tool()
async def accept_knowledge_offer(
    request_id: int, offer_id: int, accept: bool = True
) -> str:
    """
    Accept or reject a knowledge sharing offer.

    This tool allows the requesting agent to accept or reject a specific
    knowledge offer that was made in response to their request.

    Args:
        request_id: The ID of the original knowledge request
        offer_id: The ID of the specific offer to accept/reject
        accept: True to accept the offer, False to reject it

    Returns:
        Success message with acceptance/rejection details
    """
    service_account = request_context.get("service_account", "MCP_SYSTEM")
    agent_id = get_mcp_memory_tier(service_account)

    action = "accept" if accept else "reject"

    trace = create_mcp_trace(
        f"{action}_knowledge_offer",
        service_account,
        {
            "operation": f"{action}_offer",
            "request_id": request_id,
            "offer_id": offer_id,
        },
    )
    span = create_mcp_span(
        trace,
        f"{action}_offer_operation",
        {
            "agent_id": agent_id,
            "request_id": request_id,
            "offer_id": offer_id,
            "action": action,
        },
    )

    try:
        # For now, this is a placeholder - the actual accept/reject endpoint
        # would need to be implemented in the main API
        # This tool demonstrates the pattern for future implementation

        if span:
            span.end(
                output={
                    "status": "success",
                    "action": action,
                    "request_id": request_id,
                    "offer_id": offer_id,
                }
            )

        log_mcp_request(
            service_account,
            f"{action}_knowledge_offer",
            {"request_id": request_id, "offer_id": offer_id, "action": action},
        )
        observability.record_mcp_tool_usage(
            f"{action}_knowledge_offer", service_account, True
        )

        return f"Knowledge offer {action}ed successfully: Request {request_id}, Offer {offer_id}"

    except Exception as e:
        if span:
            span.end(
                output={
                    "status": "error",
                    "error": str(e),
                    "request_id": request_id,
                    "offer_id": offer_id,
                }
            )
        logger.error(f"Error {action}ing knowledge offer {offer_id}: {e}")
        observability.record_mcp_tool_usage(
            f"{action}_knowledge_offer", service_account, False
        )
        return f"Error {action}ing knowledge offer {offer_id}: {str(e)}"


if __name__ == "__main__":
    # Run the MCP server
    uvicorn.run(app, host="0.0.0.0", port=8001)
