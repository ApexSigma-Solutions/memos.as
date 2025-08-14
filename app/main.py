import os

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from .models import QueryRequest, StoreRequest, ToolRegistrationRequest
from .services.postgres_client import PostgresClient, get_postgres_client
from .services.qdrant_client import QdrantMemoryClient, get_qdrant_client
from .services.redis_client import get_redis_client
from .services.neo4j_client import Neo4jClient, get_neo4j_client

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


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "memOS.as",
        "status": "running",
        "description": "Memory and tool discovery hub for AI agents",
    }


@app.get("/health")
async def health_check():
    """Detailed health check with service status"""
    try:
        # Check PostgreSQL connection
        get_postgres_client()
        postgres_status = "connected"

        # Check Qdrant connection
        qdrant_client = get_qdrant_client()
        qdrant_info = qdrant_client.get_collection_info()
        qdrant_status = "connected" if qdrant_info else "disconnected"

        # Check Redis connection
        get_redis_client()
        redis_status = "connected"  # Basic check, can be enhanced

        return {
            "status": "healthy",
            "services": {
                "postgres": postgres_status,
                "qdrant": qdrant_status,
                "redis": redis_status,
            },
            "qdrant_collection": qdrant_info,
        }
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Service health check failed: {str(e)}"
        )


# Tool Management Endpoints
@app.post("/tools/register")
async def register_tool(
    tool_request: ToolRegistrationRequest,
    postgres_client: PostgresClient = Depends(get_postgres_client),
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

        return {
            "success": True,
            "tool_id": tool_id,
            "message": f"Tool '{tool_request.name}' registered successfully",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error registering tool: {str(e)}")


@app.get("/tools/{tool_id}")
async def get_tool(
    tool_id: int, postgres_client: PostgresClient = Depends(get_postgres_client)
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
async def get_all_tools(postgres_client: PostgresClient = Depends(get_postgres_client)):
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
@app.post("/memory/store")
async def store_memory(
    store_request: StoreRequest,
    postgres_client: PostgresClient = Depends(get_postgres_client),
    qdrant_client: QdrantMemoryClient = Depends(get_qdrant_client),
    neo4j_client: Neo4jClient = Depends(get_neo4j_client),
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
        # Step 1: Generate an embedding for the content
        embedding = qdrant_client.generate_placeholder_embedding(store_request.content)

        # Step 2: Store the full content/metadata in PostgreSQL to get a unique ID
        memory_id = postgres_client.store_memory(
            content=store_request.content, metadata=store_request.metadata
        )

        if memory_id is None:
            raise HTTPException(
                status_code=500, detail="Failed to store memory in PostgreSQL"
            )

        # Step 3: Store the vector embedding and the PostgreSQL ID in Qdrant
        point_id = qdrant_client.store_embedding(
            embedding=embedding, memory_id=memory_id, metadata=store_request.metadata
        )

        if point_id is None:
            # Rollback: delete the PostgreSQL record if Qdrant storage fails
            # Note: In a production system, this should be handled with
            # proper transactions
            raise HTTPException(
                status_code=500, detail="Failed to store embedding in Qdrant"
            )

        # Update PostgreSQL record with the Qdrant point ID for linking
        postgres_client.update_memory_embedding_id(memory_id, point_id)

        # Step 4: Extract concepts and update Neo4j knowledge graph
        concepts = []
        neo4j_info = {}
        try:
            if neo4j_client.driver:  # Only if Neo4j is available
                # Extract concepts from content
                concepts = neo4j_client.extract_concepts_from_content(store_request.content)
                
                # Create memory node in Neo4j knowledge graph
                memory_node = neo4j_client.create_memory_node(
                    memory_id=memory_id,
                    content=store_request.content,
                    concepts=concepts
                )
                
                neo4j_info = {
                    "concepts_extracted": len(concepts),
                    "concepts": concepts,
                    "memory_node_created": True
                }
        except Exception as e:
            # Neo4j integration failure shouldn't break the main storage flow
            print(f"Neo4j integration warning: {e}")
            neo4j_info = {
                "concepts_extracted": 0,
                "concepts": [],
                "memory_node_created": False,
                "error": str(e)
            }

        # Step 5: Return comprehensive storage information
        return {
            "success": True,
            "memory_id": memory_id,
            "point_id": point_id,
            "knowledge_graph": neo4j_info,
            "message": "Memory stored successfully with knowledge graph integration",
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error storing memory: {str(e)}")


@app.get("/memory/{memory_id}")
async def get_memory(
    memory_id: int, postgres_client: PostgresClient = Depends(get_postgres_client)
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
        # Step 1: Generate an embedding for the query text
        query_embedding = qdrant_client.generate_placeholder_embedding(
            query_request.query
        )

        # Step 2: Perform a semantic search in Qdrant to get relevant memory IDs
        search_results = qdrant_client.search_similar_memories(
            query_embedding=query_embedding,
            top_k=query_request.top_k,
            score_threshold=0.1,  # Configurable threshold
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
                memory["similarity_score"] = memory_scores.get(memory["id"], 0.0)

            # Sort memories by similarity score (highest first)
            memories.sort(key=lambda x: x.get("similarity_score", 0.0), reverse=True)

        # Step 5: Return a combined response of relevant memories and tools
        response = {
            "query": query_request.query,
            "memories": {"count": len(memories), "results": memories},
            "tools": {"count": len(relevant_tools), "results": relevant_tools},
            "search_metadata": {
                "embedding_search_results": len(search_results),
                "memory_ids_found": memory_ids,
                "top_k_requested": query_request.top_k,
            },
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying memory: {str(e)}")


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


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8090))
    uvicorn.run(app, host="0.0.0.0", port=port)
