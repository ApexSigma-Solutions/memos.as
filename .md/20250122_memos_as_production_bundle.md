# memOS.as Production Bundle - 2025-01-22

**Architecture**: Memory Operations Service (memOS) with tiered storage system
**Framework**: FastAPI with PostgreSQL, Qdrant, Neo4j, Redis integration
**Purpose**: Multi-tier memory management with episodic, procedural, and semantic storage

## Core Production Components

### Memory Service Architecture
```python
class ObservabilityService:
    def __init__(self):
        # Initialize Prometheus, Loki, Jaeger, Grafana integration
        self._setup_logging()
        self._setup_metrics()
        self._setup_tracing()

    def instrument_fastapi(self, app):
        # OpenTelemetry FastAPI instrumentation with metrics middleware
        @app.middleware("http")
        async def metrics_middleware(request, call_next):
            start_time = time.time()
            method = request.method
            path = request.url.path
            response = await call_next(request)
            status_code = response.status_code
            duration = time.time() - start_time
            # Record metrics
            return response
```

### Database Models
```python
class Memory(Base):
    __tablename__ = "memories"
    id = Column(Integer, primary_key=True)
    content = Column(Text, nullable=False)
    memory_metadata = Column(JSON)
    embedding_id = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class RegisteredTool(Base):
    __tablename__ = "registered_tools"
    name = Column(String(255), nullable=False, unique=True)
    description = Column(Text, nullable=False)
    usage = Column(Text, nullable=False)
    tags = Column(JSON, nullable=True)
```

### Memory Storage Endpoints
```python
@app.post("/memory/store")
async def store_memory(store_request: StoreRequest):
    # Step 1: Generate embedding for content
    embedding = qdrant_client.generate_placeholder_embedding(store_request.content)

    # Step 2: Store full content/metadata in PostgreSQL
    memory_id = postgres_client.store_memory(
        store_request.content, store_request.metadata
    )

    # Step 3: Store vector embedding in Qdrant
    point_id = qdrant_client.store_embedding(
        embedding, memory_id, store_request.metadata
    )

    # Step 4: Extract concepts and update Neo4j knowledge graph
    concepts = neo4j_client.extract_concepts_from_content(store_request.content)
    memory_node = neo4j_client.create_memory_node(
        memory_id, store_request.content, concepts
    )

    return {
        "memory_id": memory_id,
        "embedding_id": point_id,
        "concepts_extracted": concepts,
        "neo4j_node": memory_node
    }

@app.post("/memory/query")
async def query_memories(query_request: QueryRequest):
    # Step 1: Generate embedding for query
    query_embedding = qdrant_client.generate_placeholder_embedding(query_request.query)

    # Step 2: Semantic search in Qdrant
    search_results = qdrant_client.search_similar_memories(
        query_embedding, query_request.top_k, score_threshold=0.1
    )

    # Step 3: Tool discovery in PostgreSQL
    relevant_tools = postgres_client.get_tools_by_context(
        query_request.query, limit=5
    )

    # Step 4: Retrieve full memory entries
    memory_ids = [result["memory_id"] for result in search_results]
    memories = postgres_client.get_memories_by_ids(memory_ids)

    return {
        "memories": memories,
        "tools": relevant_tools,
        "total_memories": len(memories),
        "total_tools": len(relevant_tools)
    }
```

### Tier-Specific Storage
```python
@app.post("/memory/tier/{tier}/store")
async def store_memory_tier(tier: int, store_request: StoreRequest):
    if tier == 1:  # Redis (Working Memory & Cache)
        key = hashlib.md5(store_request.content.encode()).hexdigest()
        redis_client.store_memory(key, {
            "content": store_request.content,
            "metadata": store_request.metadata
        })
        return {"tier": 1, "storage": "redis", "key": key}

    elif tier == 2:  # PostgreSQL & Qdrant (Episodic & Procedural)
        # Store in PostgreSQL then Qdrant following main flow
        return await store_memory(store_request)

    elif tier == 3:  # Neo4j (Semantic Memory)
        # Store directly in Neo4j with concept extraction
        concepts = neo4j_client.extract_concepts_from_content(store_request.content)
        memory_node = neo4j_client.store_memory(memory_id, store_request.content, concepts)
        return {"tier": 3, "storage": "neo4j", "memory_node": memory_node}
```

### Database Clients

#### PostgreSQL Client
```python
class PostgresClient:
    def store_memory(self, content: str, metadata: Optional[Dict] = None, embedding_id: str = None) -> Optional[int]:
        memory = Memory(
            content=content,
            memory_metadata=metadata,
            embedding_id=embedding_id
        )
        session.add(memory)
        session.commit()
        return memory.id

    def register_tool(self, name: str, description: str, usage: str, tags: List[str] = None) -> Optional[int]:
        tool = RegisteredTool(
            name=name, description=description, usage=usage, tags=tags
        )
        session.add(tool)
        session.commit()
        return tool.id
```

#### Qdrant Client
```python
class QdrantMemoryClient:
    def store_embedding(self, embedding: List[float], memory_id: int, metadata: Dict = None) -> Optional[str]:
        point_id = str(uuid.uuid4())
        payload = {"memory_id": memory_id, "metadata": metadata or {}}
        point = PointStruct(id=point_id, vector=embedding, payload=payload)
        self.client.upsert(collection_name=self.collection_name, points=[point])
        return point_id

    def search_similar_memories(self, query_embedding: List[float], top_k: int = 5, score_threshold: float = 0.5):
        search_result = self.client.search(
            collection_name=self.collection_name,
            query_vector=query_embedding,
            limit=top_k,
            score_threshold=score_threshold
        )
        return [{"memory_id": hit.payload["memory_id"], "score": hit.score} for hit in search_result]
```

#### Neo4j Client
```python
class Neo4jClient:
    def create_memory_node(self, memory_id: int, content: str, concepts: List[str] = None) -> Dict:
        with self.get_session() as session:
            result = session.run(
                "CREATE (m:Memory {id: $memory_id, content: $content, created_at: datetime()}) RETURN m",
                memory_id=memory_id, content=content
            )
            memory_node = result.single()["m"]

            # Create concept relationships
            for concept in concepts or []:
                self._create_concept_relationship(session, memory_id, concept)

            return dict(memory_node)

    def extract_concepts_from_content(self, content: str) -> List[str]:
        words = content.lower().split()
        concepts = []
        for word in words:
            if len(word) > 4 and word.isalpha():
                concepts.append(word)
        return list(set(concepts))[:10]  # Return first 10 unique concepts
```

### Knowledge Graph Operations
```python
@app.post("/graph/query")
async def query_graph(query_request: GraphQueryRequest):
    query = f"MATCH (n:{query_request.node_label})"
    if query_request.filters:
        filter_conditions = [f"n.{k} = ${k}" for k in query_request.filters.keys()]
        query += f" WHERE {' AND '.join(filter_conditions)}"

    if query_request.return_properties:
        props = ", ".join([f"n.{prop}" for prop in query_request.return_properties])
        query += f" RETURN {props}"
    else:
        query += " RETURN n"

    result = neo4j_client.run_cypher_query(query, query_request.filters)
    return {"results": result, "query_executed": query}

@app.get("/graph/related/{node_id}")
async def get_related_nodes(node_id: str):
    result = neo4j_client.get_related_nodes(node_id)
    return result

@app.get("/graph/path/{start_node_id}/{end_node_id}")
async def get_shortest_path(start_node_id: str, end_node_id: str):
    result = neo4j_client.get_shortest_path(start_node_id, end_node_id)
    return result
```

### Health & Metrics
```python
@app.get("/health")
async def health_check():
    postgres_status = "connected"
    qdrant_info = qdrant_client.get_collection_info()
    qdrant_status = "connected" if qdrant_info else "disconnected"
    redis_status = "connected"

    return {
        "status": "healthy",
        "services": {
            "postgres": postgres_status,
            "qdrant": qdrant_status,
            "redis": redis_status,
            "neo4j": "connected" if neo4j_client.driver else "disconnected"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/metrics")
async def get_metrics():
    return observability.get_metrics()
```

**Key Features**: Tiered memory storage, semantic search, concept extraction, tool discovery, observability integration, knowledge graph management, multi-database coordination
