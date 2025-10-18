import logging
import os
from typing import Optional


from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from apexsigma_core.models import StoreRequest, QueryRequest
from app.models import (
    GraphQueryRequest,
    LLMCacheRequest,
    LLMPerformanceRequest,
    LLMUsageRequest,
    ToolRegistrationRequest,
)
from app.schemas import (
    MCP_TIER_MAPPING,
    KnowledgeShareOffer,
    KnowledgeShareRequest,
    MCPTier,
)
from app.services.neo4j_client import Neo4jClient, get_neo4j_client
from app.services.observability import (
    ObservabilityService,
    get_observability,
    trace_async,
)
from app.services.postgres_client import PostgresClient, get_postgres_client
from app.services.qdrant_client import QdrantMemoryClient, get_qdrant_client
from app.services.redis_client import RedisClient, get_redis_client

# Initialize FastAPI app
app = FastAPI(
    title="memOS.as",
    description="Memory and tool discovery hub for the DevEnviro AI agent ecosystem",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize logging
logger = logging.getLogger(__name__)

# Initialize observability lazily on startup to avoid creating DB/network
# connections during module import (which breaks pytest collection).


@app.on_event("startup")
async def startup_event():
    """
    Initialize observability instrumentation for the application during startup.
    
    Attempts to instrument the FastAPI app and configured database clients via the Observability service; instrumentation failures are ignored to allow startup in tests or minimal environments.
    """
    obs = get_observability()
    try:
        obs.instrument_fastapi(app)
        obs.instrument_database_clients()
    except Exception:
        # During tests or in minimal environments these may fail; ignore.
        pass


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "memOS.as",
        "status": "running",
        "description": "Memory and tool discovery hub for AI agents",
    }


@app.get("/cache/stats")
async def get_cache_stats(
    redis_client: RedisClient = Depends(get_redis_client),
):
    """
    Get Redis cache statistics and performance metrics.
    """
    try:
        if not redis_client.is_connected():
            return {
                "error": "Redis not connected",
                "connected": False,
                "stats": None,
            }

        stats = redis_client.get_cache_stats()
        return {
            "connected": True,
            "stats": stats,
            "message": "Cache statistics retrieved successfully",
        }

    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        raise HTTPException(
            status_code=500, detail=f"Error getting cache stats: {str(e)}"
        )


@app.delete("/cache/clear")
async def clear_cache(
    pattern: str = "*",
    redis_client: RedisClient = Depends(get_redis_client),
):
    """
    Clear cache entries matching the specified pattern.
    Default pattern '*' clears all cache entries.
    """
    try:
        if not redis_client.is_connected():
            return {
                "error": "Redis not connected",
                "connected": False,
                "cleared": 0,
            }

        cleared_count = redis_client.clear_cache_pattern(pattern)
        return {
            "connected": True,
            "pattern": pattern,
            "cleared": cleared_count,
            "message": f"Cleared {cleared_count} cache entries",
        }

    except Exception as e:
        logger.error(f"Error clearing cache: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@app.get("/health")
async def health_check(
    observability: ObservabilityService = Depends(get_observability),
):
    """Enhanced health check with graceful database error handling"""
    health_data = observability.health_check()
    services_status = {}

    # Check PostgreSQL with graceful fallback
    try:
        postgres_client = get_postgres_client()
        # Test with a simple query
        with postgres_client.get_session() as session:
            from sqlalchemy import text

            session.execute(text("SELECT 1"))
        services_status["postgres"] = "connected"
        observability.active_connections.labels(database="postgresql").set(1)
    except Exception as e:
        services_status["postgres"] = f"disconnected: {str(e)[:100]}"
        observability.active_connections.labels(database="postgresql").set(0)

    # Check Qdrant with graceful fallback
    try:
        qdrant_client = get_qdrant_client()
        qdrant_info = qdrant_client.get_collection_info()
        services_status["qdrant"] = "connected" if qdrant_info else "disconnected"
        observability.active_connections.labels(database="qdrant").set(
            1 if qdrant_info else 0
        )
    except Exception as e:
        services_status["qdrant"] = f"disconnected: {str(e)[:100]}"
        qdrant_info = None
        observability.active_connections.labels(database="qdrant").set(0)

    # Check Redis with graceful fallback
    try:
        redis_client = get_redis_client()
        redis_client.client.ping()
        services_status["redis"] = "connected"
        observability.active_connections.labels(database="redis").set(1)
    except Exception as e:
        services_status["redis"] = f"disconnected: {str(e)[:100]}"
        observability.active_connections.labels(database="redis").set(0)

    # Check Neo4j with graceful fallback
    try:
        neo4j_client = get_neo4j_client()
        if neo4j_client.driver:
            with neo4j_client.get_session() as session:
                session.run("RETURN 1")
            services_status["neo4j"] = "connected"
        else:
            services_status["neo4j"] = "disconnected: driver not initialized"
    except Exception as e:
        services_status["neo4j"] = f"disconnected: {str(e)[:100]}"

    # Log health check with detailed status
    observability.log_structured(
        "info",
        "Health check performed",
        **{f"{db}_status": status for db, status in services_status.items()},
    )

    # Determine if integration is ready (PostgreSQL is critical)
    integration_ready = "connected" in services_status.get("postgres", "")

    health_data.update(
        {
            "services": services_status,
            "integration_ready": integration_ready,
            "qdrant_collection": qdrant_info if "qdrant_info" in locals() else None,
            "operational_mode": (
                "full"
                if all("connected" in status for status in services_status.values())
                else "degraded"
            ),
        }
    )

    return health_data


@app.get("/metrics")
async def get_metrics(
    observability: ObservabilityService = Depends(get_observability),
):
    """Prometheus metrics endpoint for DevEnviro monitoring stack."""
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(observability.get_metrics(), media_type="text/plain")


# Tool Management Endpoints
@app.post("/tools/register")
async def register_tool(
    tool_request: ToolRegistrationRequest,
    postgres_client: PostgresClient = Depends(get_postgres_client),
    redis_client: RedisClient = Depends(get_redis_client),
):
    """
    Register a new tool in the PostgreSQL registered_tools table.

    This endpoint allows agents to register their capabilities so other agents
    can discover and use them via the /memory/query endpoint.
    """
    try:
        tool_id = postgres_client.register_tool(
            name=tool_request.name,
            description=tool_request.description,
            usage=tool_request.usage,
            tags=tool_request.tags,
        )

        if tool_id is None:
            raise HTTPException(
                status_code=400,
                detail="Failed to register tool. Tool name might already exist.",
            )

        # Invalidate tool caches after successful registration
        if redis_client.is_connected():
            redis_client.invalidate_tool_caches()

        return {
            "success": True,
            "tool_id": tool_id,
            "message": f"Tool '{tool_request.name}' registered successfully",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering tool: {str(e)}")


@app.get("/tools/{tool_id}")
async def get_tool(
    tool_id: int,
    postgres_client: PostgresClient = Depends(get_postgres_client),
):
    """Get a specific tool by ID"""
    try:
        tool = postgres_client.get_tool(tool_id)

        if tool is None:
            raise HTTPException(status_code=404, detail="Tool not found")

        return tool

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tool: {str(e)}")


@app.get("/tools")
async def get_all_tools(
    postgres_client: PostgresClient = Depends(get_postgres_client),
):
    """Get all registered tools"""
    try:
        tools = postgres_client.get_all_tools()
        return {"tools": tools, "count": len(tools)}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving tools: {str(e)}")


@app.get("/tools/search")
async def search_tools(
    query: str,
    limit: int = 10,
    postgres_client: PostgresClient = Depends(get_postgres_client),
):
    """Search for tools by query context"""
    try:
        tools = postgres_client.get_tools_by_context(query, limit)
        return {"tools": tools, "count": len(tools), "query": query}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching tools: {str(e)}")


# Memory Management Endpoints
@app.post("/memory/mcp/{mcp_tier}/store")
async def store_mcp_memory(
    mcp_tier: MCPTier,
    store_request: StoreRequest,
    postgres_client: PostgresClient = Depends(get_postgres_client),
    qdrant_client: QdrantMemoryClient = Depends(get_qdrant_client),
    redis_client: RedisClient = Depends(get_redis_client),
    neo4j_client: Neo4jClient = Depends(get_neo4j_client),
    observability: ObservabilityService = Depends(get_observability),
):
    """
    Store a new memory in a specific MCP logical tier.
    """
    storage_tier = MCP_TIER_MAPPING[mcp_tier].value
    return await store_memory_by_tier(
        tier=storage_tier,
        store_request=store_request,
        postgres_client=postgres_client,
        qdrant_client=qdrant_client,
        redis_client=redis_client,
        neo4j_client=neo4j_client,
        observability=observability,
    )


@app.post("/memory/store")
@trace_async("memory.store")
async def store_memory(
    store_request: StoreRequest,
    postgres_client: PostgresClient = Depends(get_postgres_client),
    qdrant_client: QdrantMemoryClient = Depends(get_qdrant_client),
    redis_client: RedisClient = Depends(get_redis_client),
    neo4j_client: Neo4jClient = Depends(get_neo4j_client),
    observability: ObservabilityService = Depends(get_observability),
):
    """
    Store a new memory with embeddings and knowledge graph updates.

    Logic:
    1. Generate an embedding for the content (using placeholder function initially)
    2. Store the full content/metadata in PostgreSQL to get a unique ID
    3. Store the vector embedding and the PostgreSQL ID in Qdrant
    4. Extract concepts from content and update Neo4j knowledge graph
    5. Return the PostgreSQL ID and knowledge graph information
    """
    try:
        # Debug: verify dependency types
        try:
            observability.log_structured(
                "info",
                "store_memory dependency types",
                postgres_client_type=str(type(postgres_client)),
                qdrant_client_type=str(type(qdrant_client)),
                redis_client_type=str(type(redis_client)),
                neo4j_client_type=str(type(neo4j_client)),
            )
        except Exception:
            pass
        import time

        start_time = time.time()

        # Step 1: Generate an embedding for the content (with caching)
        # First check if we have cached embedding for this content
        cached_embedding = redis_client.get_cached_embedding(store_request.content)
        if cached_embedding:
            embedding = cached_embedding
            observability.record_memory_operation("embedding_cache_hit", "success")
        else:
            embedding = qdrant_client.generate_placeholder_embedding(
                store_request.content
            )
            # Cache the generated embedding
            redis_client.cache_embedding(store_request.content, embedding)
            observability.record_memory_operation("embedding_generation", "success")

        # Step 2: Store the full content/metadata in PostgreSQL to get a unique ID
        postgres_start = time.time()
        memory_id = postgres_client.store_memory(
            content=store_request.content,
            agent_id=store_request.agent_id,
            metadata=store_request.metadata,
        )
        postgres_duration = time.time() - postgres_start

        if memory_id is None:
            observability.record_memory_operation(
                "postgres_store", "failed", "tier2", postgres_duration
            )
            raise HTTPException(
                status_code=500, detail="Failed to store memory in PostgreSQL"
            )

        observability.record_memory_operation(
            "postgres_store", "success", "tier2", postgres_duration
        )

        # Step 3: Store the vector embedding and the PostgreSQL ID in Qdrant (with graceful fallback)
        point_id = None
        qdrant_success = False

        try:
            qdrant_start = time.time()
            point_id = qdrant_client.store_embedding(
                embedding=embedding,
                memory_id=memory_id,
                agent_id=store_request.agent_id,
                metadata=store_request.metadata,
            )
            qdrant_duration = time.time() - qdrant_start

            if point_id is not None:
                observability.record_memory_operation(
                    "qdrant_store", "success", "tier2", qdrant_duration
                )
                # Update PostgreSQL record with the Qdrant point ID for linking
                postgres_client.update_memory_embedding_id(memory_id, point_id)
                qdrant_success = True
            else:
                observability.record_memory_operation(
                    "qdrant_store", "failed", "tier2", qdrant_duration
                )

        except Exception as e:
            qdrant_duration = (
                time.time() - qdrant_start if "qdrant_start" in locals() else 0
            )
            observability.record_memory_operation(
                "qdrant_store", "failed", "tier2", qdrant_duration
            )
            observability.log_structured(
                "warning",
                "Qdrant storage failed, continuing with degraded functionality",
                memory_id=memory_id,
                error=str(e),
            )

        # Step 4: Extract concepts and update Neo4j knowledge graph
        concepts = []
        neo4j_info = {}
        try:
            if neo4j_client.driver:  # Only if Neo4j is available
                neo4j_start = time.time()

                # Extract concepts from content
                concepts = neo4j_client.extract_concepts_from_content(
                    store_request.content
                )
                observability.record_concepts_extracted(len(concepts))

                # Create memory node in Neo4j knowledge graph
                memory_node = neo4j_client.create_memory_node(
                    memory_id=memory_id,
                    content=store_request.content,
                    concepts=concepts,
                )

                neo4j_duration = time.time() - neo4j_start
                observability.record_memory_operation(
                    "neo4j_store", "success", "tier3", neo4j_duration
                )
                observability.record_knowledge_graph_operation(
                    "create_memory_node", "Memory"
                )
                for concept in concepts:
                    observability.record_knowledge_graph_operation(
                        "create_concept_node", "Concept"
                    )

                neo4j_info = {
                    "concepts_extracted": len(concepts),
                    "concepts": concepts,
                    "memory_node_created": True,
                }

                # Log successful knowledge graph update
                observability.log_structured(
                    "info",
                    "Knowledge graph updated",
                    memory_id=memory_id,
                    concepts_count=len(concepts),
                    duration=neo4j_duration,
                )

        except Exception as e:
            # Neo4j integration failure shouldn't break the main storage flow
            observability.record_memory_operation("neo4j_store", "failed", "tier3")
            observability.log_structured(
                "warning",
                "Neo4j integration failed",
                memory_id=memory_id,
                error=str(e),
            )
            neo4j_info = {
                "concepts_extracted": 0,
                "concepts": [],
                "memory_node_created": False,
                "error": str(e),
            }

        # Step 5: Invalidate related caches after successful storage
        if redis_client.is_connected():
            try:
                redis_client.invalidate_memory_caches(memory_id)
                observability.log_structured(
                    "info", "Memory caches invalidated", memory_id=memory_id
                )
            except Exception as e:
                observability.log_structured(
                    "warning",
                    "Failed to invalidate memory caches",
                    memory_id=memory_id,
                    error=str(e),
                )

        # Step 6: Return comprehensive storage information with degraded mode indicators
        storage_status = {
            "postgres": True,  # Always true if we reach this point
            "qdrant": qdrant_success,
            "neo4j": neo4j_info.get("memory_node_created", False),
        }

        operational_mode = "full" if all(storage_status.values()) else "degraded"

        return {
            "success": True,
            "memory_id": memory_id,
            "point_id": point_id,
            "knowledge_graph": neo4j_info,
            "storage_status": storage_status,
            "operational_mode": operational_mode,
            "message": f"Memory stored successfully in {operational_mode} mode",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing memory: {str(e)}")


@app.post("/memory/{tier}/store")
@trace_async("memory.store_by_tier")
async def store_memory_by_tier(
    tier: str,
    store_request: StoreRequest,
    postgres_client: PostgresClient = Depends(get_postgres_client),
    qdrant_client: QdrantMemoryClient = Depends(get_qdrant_client),
    redis_client: RedisClient = Depends(get_redis_client),
    neo4j_client: Neo4jClient = Depends(get_neo4j_client),
    observability: ObservabilityService = Depends(get_observability),
):
    """
    Store a new memory in a specific tier.
    """
    if tier == "1":
        # Tier 1: Redis (Working Memory & Cache)
        try:
            # For Redis, we need a key. We can use a hash of the content as the key.
            import hashlib

            key = hashlib.md5(store_request.content.encode()).hexdigest()
            redis_client.store_memory(key, store_request.dict())
            observability.record_memory_operation("redis_store", "success", "tier1")
            return {
                "success": True,
                "tier": 1,
                "memory_id": key,
                "key": key,
                "message": "Memory stored in Redis",
            }
        except Exception as e:
            observability.record_memory_operation("redis_store", "failed", "tier1")
            raise HTTPException(
                status_code=500,
                detail=f"Error storing memory in Redis: {str(e)}",
            )
    elif tier == "2":
        # Tier 2: PostgreSQL & Qdrant (Episodic & Procedural Memory)
        result = await store_memory(
            store_request,
            postgres_client=postgres_client,
            qdrant_client=qdrant_client,
            redis_client=redis_client,
            neo4j_client=neo4j_client,
            observability=observability,
        )
        # Ensure memory_id and tier are included in the response
        if isinstance(result, dict):
            if "memory_id" not in result and "postgres" in result:
                try:
                    result["memory_id"] = result["postgres"].get("memory_id")
                except Exception:
                    pass
            # Include tier information for client compatibility
            result.setdefault("tier", 2)
        return result
    elif tier == "3":
        # Tier 3: Neo4j (Semantic Memory)
        try:
            # First, store in PostgreSQL to get a unique ID
            memory_id = postgres_client.store_memory(
                content=store_request.content, metadata=store_request.metadata
            )
            if not memory_id:
                raise HTTPException(
                    status_code=500,
                    detail="Failed to store memory in PostgreSQL",
                )
            # Then, attempt to store in Neo4j with the new ID
            neo4j_info = {
                "memory_node_created": False,
                "concepts_extracted": 0,
                "concepts": [],
            }
            try:
                if neo4j_client.driver:
                    concepts = neo4j_client.extract_concepts_from_content(
                        store_request.content
                    )
                    memory_node = neo4j_client.store_memory(
                        memory_id, store_request.content, concepts
                    )
                    observability.record_memory_operation(
                        "neo4j_store", "success", "tier3"
                    )
                    neo4j_info.update(
                        {
                            "memory_node_created": True,
                            "concepts_extracted": len(concepts),
                            "concepts": concepts,
                            "node": memory_node,
                        }
                    )
                else:
                    observability.record_memory_operation(
                        "neo4j_store", "failed", "tier3"
                    )
                    neo4j_info["error"] = "Neo4j driver not initialized"
            except Exception as e:
                # Degrade gracefully if Neo4j fails
                observability.record_memory_operation("neo4j_store", "failed", "tier3")
                neo4j_info["error"] = str(e)

            # Return success with degraded mode info if needed
            operational_mode = (
                "full" if neo4j_info.get("memory_node_created") else "degraded"
            )
            response = {
                "success": True,
                "tier": 3,
                "memory_id": memory_id,
                "knowledge_graph": neo4j_info,
                "operational_mode": operational_mode,
                "message": f"Memory stored in {operational_mode} mode",
            }
            if "node" in neo4j_info:
                response["node"] = neo4j_info["node"]
            return response
        except Exception as e:
            observability.record_memory_operation("neo4j_store", "failed", "tier3")
            raise HTTPException(
                status_code=500,
                detail=f"Error storing memory in Neo4j: {str(e)}",
            )
    else:
        raise HTTPException(
            status_code=400,
            detail="Invalid memory tier specified. Use 1, 2, or 3.",
        )


@app.get("/memory/{memory_id}")
async def get_memory(
    memory_id: int,
    postgres_client: PostgresClient = Depends(get_postgres_client),
):
    """Get a specific memory by ID"""
    try:
        memory = postgres_client.get_memory(memory_id)

        if memory is None:
            raise HTTPException(status_code=404, detail="Memory not found")

        return memory

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving memory: {str(e)}"
        )


@app.post("/memory/query")
async def query_memory(
    query_request: QueryRequest,
    postgres_client: PostgresClient = Depends(get_postgres_client),
    qdrant_client: QdrantMemoryClient = Depends(get_qdrant_client),
    redis_client: RedisClient = Depends(get_redis_client),
):
    """
    Query memories using semantic search and tool discovery.

    Logic:
    1. Generate an embedding for the query text
    2. Perform a semantic search in Qdrant to get relevant memory IDs
    3. Query PostgreSQL for tools that match the query context (Tool Discovery Logic)
    4. Retrieve full memory entries from PostgreSQL
    5. Return a combined response of relevant memories and tools
    """
    try:
        # Step 0: Check for cached query results
        if redis_client.is_connected():
            cached_results = redis_client.get_cached_query_result(
                query_request.query, query_request.top_k
            )
            if cached_results:
                # Return cached results with cache indicator
                return {
                    "query": query_request.query,
                    "top_k": query_request.top_k,
                    "memories": cached_results,
                    "tools": [],  # Tools not cached in this implementation
                    "memory_count": len(cached_results),
                    "tool_count": 0,
                    "cached": True,
                    "message": "Results retrieved from cache",
                }

        # Step 1: Generate an embedding for the query text (with caching)
        cached_embedding = redis_client.get_cached_embedding(query_request.query)
        if cached_embedding:
            query_embedding = cached_embedding
        else:
            query_embedding = qdrant_client.generate_placeholder_embedding(
                query_request.query
            )
            # Cache the generated embedding
            redis_client.cache_embedding(query_request.query, query_embedding)

        # Step 2: Perform a semantic search in Qdrant to get relevant memory IDs
        agent_to_query = query_request.agent_id
        search_results = qdrant_client.search_similar_memories(
            query_embedding=query_embedding,
            top_k=query_request.top_k,
            score_threshold=0.1,  # Configurable threshold
            agent_id=agent_to_query,
        )

        # Extract memory IDs from search results
        memory_ids = [
            result["memory_id"] for result in search_results if result["memory_id"]
        ]

        # Step 3: Query PostgreSQL for tools that match the query context
        # (Tool Discovery Logic)
        relevant_tools = postgres_client.get_tools_by_context(
            query_context=query_request.query,
            limit=5,  # Limit tools to keep response manageable
        )

        # Step 4: Retrieve full memory entries from PostgreSQL
        memories = []
        if memory_ids:
            memories = postgres_client.get_memories_by_ids(memory_ids)

            # Enrich memories with similarity scores from Qdrant
            memory_scores = {
                result["memory_id"]: result["score"] for result in search_results
            }
            for memory in memories:
                memory["confidence_score"] = memory_scores.get(memory["id"], 0.0)

            # Sort memories by similarity score (highest first)
            memories.sort(key=lambda x: x.get("confidence_score", 0.0), reverse=True)

        # Step 6: Cache query results in Redis for future requests
        if redis_client.is_connected() and memories:
            redis_client.cache_query_result(
                query_request.query, memories, query_request.top_k
            )

        # Step 7: Return combined response of relevant memories and tools
        response = {
            "query": query_request.query,
            "memories": {"count": len(memories), "results": memories},
            "tools": {"count": len(relevant_tools), "results": relevant_tools},
            "search_metadata": {
                "embedding_search_results": len(search_results),
                "memory_ids_found": memory_ids,
                "top_k_requested": query_request.top_k,
            },
            "cached": False,
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying memory: {str(e)}")


# Knowledge Sharing Endpoints
@app.post("/memory/share/request")
async def request_knowledge(
    share_request: KnowledgeShareRequest,
    postgres_client: PostgresClient = Depends(get_postgres_client),
    observability: ObservabilityService = Depends(get_observability),
):
    request_id = postgres_client.create_knowledge_share_request(
        requester_agent_id=share_request.agent_id,  # This needs to be passed in the request
        target_agent_id=share_request.target_agent,
        query=share_request.query,
        confidence_threshold=share_request.confidence_threshold,
        sharing_policy=share_request.sharing_policy,
    )
    if request_id is None:
        raise HTTPException(
            status_code=500, detail="Failed to create knowledge share request"
        )

    observability.log_structured(
        "info",
        "Knowledge share request created",
        request_id=request_id,
        requester_agent_id=share_request.agent_id,
        target_agent_id=share_request.target_agent,
        query=share_request.query,
    )

    return {
        "message": "Knowledge share request created successfully",
        "request_id": request_id,
    }


@app.post("/memory/share/offer")
async def offer_knowledge(
    offer_request: KnowledgeShareOffer,
    postgres_client: PostgresClient = Depends(get_postgres_client),
    observability: ObservabilityService = Depends(get_observability),
):
    request = postgres_client.get_knowledge_share_request_by_id(
        offer_request.request_id
    )
    if not request:
        raise HTTPException(status_code=404, detail="Knowledge share request not found")

    if request["sharing_policy"] == "high_confidence_only":
        if offer_request.confidence_score < request["confidence_threshold"]:
            raise HTTPException(
                status_code=400,
                detail=f"Confidence score {offer_request.confidence_score} is below the threshold {request['confidence_threshold']}",
            )

    offer_id = postgres_client.create_knowledge_share_offer(
        request_id=offer_request.request_id,
        offering_agent_id=offer_request.offering_agent_id,
        memory_id=offer_request.memory_id,
        confidence_score=offer_request.confidence_score,
    )
    if offer_id is None:
        raise HTTPException(
            status_code=500, detail="Failed to create knowledge share offer"
        )

    observability.log_structured(
        "info",
        "Knowledge share offer created",
        offer_id=offer_id,
        request_id=offer_request.request_id,
        offering_agent_id=offer_request.offering_agent_id,
        memory_id=offer_request.memory_id,
        confidence_score=offer_request.confidence_score,
    )

    return {
        "message": "Knowledge share offer created successfully",
        "offer_id": offer_id,
    }


@app.get("/memory/share/pending")
async def get_pending_shares(
    agent_id: str,
    postgres_client: PostgresClient = Depends(get_postgres_client),
):
    requests = postgres_client.get_pending_knowledge_share_requests(agent_id)
    return {"pending_requests": requests}


@app.get("/memory/search")
async def search_memories(
    query: str,
    top_k: int = 5,
    postgres_client: PostgresClient = Depends(get_postgres_client),
    qdrant_client: QdrantMemoryClient = Depends(get_qdrant_client),
):
    """
    Simple memory search endpoint (alternative to POST /memory/query)
    """
    try:
        # Create QueryRequest object and use the main query logic
        query_request = QueryRequest(query=query, top_k=top_k)
        return await query_memory(query_request, postgres_client, qdrant_client)

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error searching memories: {str(e)}"
        )


# Graph Query Endpoint
@app.post("/graph/query")
async def query_graph(
    query_request: GraphQueryRequest,
    neo4j_client: Neo4jClient = Depends(get_neo4j_client),
):
    """
    Query the Neo4j knowledge graph.
    """
    try:
        # Build the Cypher query
        query = f"MATCH (n:{query_request.node_label})"
        if query_request.filters:
            query += " WHERE "
            query += " AND ".join(
                [f"n.{key} = ${key}" for key in query_request.filters.keys()]
            )

        if query_request.return_properties:
            query += f" RETURN n.{', n.'.join(query_request.return_properties)}"
        else:
            query += " RETURN n"

        # Execute the query
        result = neo4j_client.run_cypher_query(query, query_request.filters)

        return {"result": result}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying graph: {str(e)}")


@app.get("/graph/related")
async def get_related(
    node_id: str, neo4j_client: Neo4jClient = Depends(get_neo4j_client)
):
    """Get all directly connected nodes and their relationships."""
    try:
        result = neo4j_client.get_related_nodes(node_id)
        return {"result": result}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting related nodes: {str(e)}"
        )


@app.get("/graph/shortest-path")
async def get_shortest_path(
    start_node_id: str,
    end_node_id: str,
    neo4j_client: Neo4jClient = Depends(get_neo4j_client),
):
    """Calculate and return the shortest path between two nodes."""
    try:
        result = neo4j_client.get_shortest_path(start_node_id, end_node_id)
        return {"result": result}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting shortest path: {str(e)}"
        )


@app.get("/graph/subgraph")
async def get_subgraph(
    node_id: str,
    depth: int = 1,
    neo4j_client: Neo4jClient = Depends(get_neo4j_client),
):
    """Get the subgraph surrounding a central node."""
    try:
        result = neo4j_client.get_subgraph(node_id, depth)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting subgraph: {str(e)}")


# === LLM Cache Endpoints ===


@app.post("/llm/cache")
async def cache_llm_response(
    request: LLMCacheRequest,
    redis_client: RedisClient = Depends(get_redis_client),
):
    """
    Cache an LLM response for future retrieval.
    This helps reduce API costs and improve response times.
    """
    try:
        if not redis_client.is_connected():
            raise HTTPException(
                status_code=503, detail="Redis cache service unavailable"
            )

        success = redis_client.cache_llm_response(
            model=request.model,
            prompt=request.prompt,
            response="",  # Will be set by the actual LLM call
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            metadata=request.metadata,
        )

        if success:
            return {
                "message": "LLM response cached successfully",
                "model": request.model,
                "cached": True,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to cache LLM response")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error caching LLM response: {str(e)}"
        )


@app.get("/llm/cache")
async def get_cached_llm_response(
    model: str,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 1000,
    redis_client: RedisClient = Depends(get_redis_client),
):
    """
    Retrieve a cached LLM response if available.
    """
    try:
        if not redis_client.is_connected():
            raise HTTPException(
                status_code=503, detail="Redis cache service unavailable"
            )

        cached_response = redis_client.get_cached_llm_response(
            model=model,
            prompt=prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        if cached_response:
            return {
                "cached": True,
                "response": cached_response,
                "message": "Cached response retrieved successfully",
            }
        else:
            return {
                "cached": False,
                "response": None,
                "message": "No cached response found",
            }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving cached LLM response: {str(e)}"
        )


@app.post("/llm/usage")
async def track_llm_usage(
    request: LLMUsageRequest,
    redis_client: RedisClient = Depends(get_redis_client),
):
    """
    Track LLM token usage for cost monitoring and analytics.
    """
    try:
        if not redis_client.is_connected():
            raise HTTPException(
                status_code=503, detail="Redis cache service unavailable"
            )

        success = redis_client.track_llm_usage(
            model=request.model,
            prompt_tokens=request.prompt_tokens,
            completion_tokens=request.completion_tokens,
            total_tokens=request.total_tokens,
            request_id=request.request_id,
        )

        if success:
            return {
                "message": "LLM usage tracked successfully",
                "model": request.model,
                "tokens": request.total_tokens,
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to track LLM usage")

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error tracking LLM usage: {str(e)}"
        )


@app.get("/llm/usage/stats")
async def get_llm_usage_stats(
    model: Optional[str] = None,
    redis_client: RedisClient = Depends(get_redis_client),
):
    """
    Get LLM usage statistics for monitoring and cost analysis.
    """
    try:
        if not redis_client.is_connected():
            raise HTTPException(
                status_code=503, detail="Redis cache service unavailable"
            )

        stats = redis_client.get_llm_usage_stats(model)

        return {
            "stats": stats,
            "message": "LLM usage statistics retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving LLM usage stats: {str(e)}"
        )


@app.post("/llm/performance")
async def track_llm_performance(
    request: LLMPerformanceRequest,
    redis_client: RedisClient = Depends(get_redis_client),
):
    """
    Track LLM model performance metrics.
    """
    try:
        if not redis_client.is_connected():
            raise HTTPException(
                status_code=503, detail="Redis cache service unavailable"
            )

        success = redis_client.cache_model_performance(
            model=request.model,
            operation=request.operation,
            response_time=request.response_time,
            success=request.success,
            error_message=request.error_message,
        )

        if success:
            return {
                "message": "LLM performance tracked successfully",
                "model": request.model,
                "operation": request.operation,
            }
        else:
            raise HTTPException(
                status_code=500, detail="Failed to track LLM performance"
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error tracking LLM performance: {str(e)}"
        )


@app.get("/llm/performance/stats")
async def get_llm_performance_stats(
    model: str,
    operation: str,
    redis_client: RedisClient = Depends(get_redis_client),
):
    """
    Get LLM model performance statistics.
    """
    try:
        if not redis_client.is_connected():
            raise HTTPException(
                status_code=503, detail="Redis cache service unavailable"
            )

        stats = redis_client.get_model_performance(model, operation)

        if "error" in stats:
            raise HTTPException(status_code=404, detail=stats["error"])

        return {
            "stats": stats,
            "message": "LLM performance statistics retrieved successfully",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error retrieving LLM performance stats: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8090))
    uvicorn.run(app, host="0.0.0.0", port=port)