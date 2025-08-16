import os
from typing import Dict, List, Optional
from contextlib import contextmanager

from neo4j import GraphDatabase, Driver, Session

from app.services.observability import get_observability


class Neo4jClient:
    """
    Neo4j client for Tier 3 Knowledge Graph operations.

    Manages conceptual relationships between memories, tools, concepts, and agents
    to provide higher-level understanding and context awareness.
    """

    def __init__(self):
        self.observability = get_observability()
        self.uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.username = os.environ.get("NEO4J_USERNAME", "neo4j")
        self.password = os.environ.get("NEO4J_PASSWORD", "password")

        self.driver: Optional[Driver] = None
        self._connect()
        self._create_constraints()

    def _connect(self):
        """Establish connection to Neo4j database."""
        try:
            self.driver = GraphDatabase.driver(
                self.uri,
                auth=(self.username, self.password)
            )
            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.observability.log_structured("info", "Connected to Neo4j", uri=self.uri)
        except Exception as e:
            self.observability.log_structured("error", "Failed to connect to Neo4j", error=str(e))
            self.driver = None

    def _create_constraints(self):
        """Create uniqueness constraints for core node types."""
        if not self.driver:
            return

        constraints = [
            "CREATE CONSTRAINT memory_id_unique IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT tool_name_unique IF NOT EXISTS FOR (t:Tool) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT agent_name_unique IF NOT EXISTS FOR (a:Agent) REQUIRE a.name IS UNIQUE"
        ]

        with self.driver.session() as session:
            for constraint in constraints:
                try:
                    session.run(constraint)
                except Exception:
                    # Constraint might already exist
                    pass

    @contextmanager
    def get_session(self):
        """Context manager for Neo4j sessions."""
        if not self.driver:
            raise Exception("Neo4j driver not initialized")

        session = self.driver.session()
        try:
            yield session
        finally:
            session.close()

    def close(self):
        """Close the Neo4j driver connection."""
        if self.driver:
            self.driver.close()

    # Node Creation Methods

    def create_memory_node(self, memory_id: int, content: str, concepts: List[str] = None) -> Dict:
        """Create a Memory node and link it to extracted concepts."""
        concepts = concepts or []

        with self.get_session() as session:
            # Create memory node
            result = session.run(
                """
                CREATE (m:Memory {
                    id: $memory_id,
                    content: $content,
                    created_at: datetime(),
                    updated_at: datetime()
                })
                RETURN m
                """,
                memory_id=memory_id,
                content=content
            )

            memory_node = result.single()["m"]

            # Create concept nodes and relationships
            for concept in concepts:
                self._create_concept_relationship(session, memory_id, concept)

            self.observability.record_knowledge_graph_operation("create_memory_node", "Memory")
            return dict(memory_node)

    def create_tool_node(self, name: str, description: str, usage: str, tags: List[str] = None) -> Dict:
        """Create a Tool node."""
        tags = tags or []

        with self.get_session() as session:
            result = session.run(
                """
                MERGE (t:Tool {name: $name})
                SET t.description = $description,
                    t.usage = $usage,
                    t.tags = $tags,
                    t.updated_at = datetime()
                RETURN t
                """,
                name=name,
                description=description,
                usage=usage,
                tags=tags
            )

            self.observability.record_knowledge_graph_operation("create_tool_node", "Tool")
            return dict(result.single()["t"])

    def create_concept_node(self, name: str, description: str = None) -> Dict:
        """Create a Concept node."""
        with self.get_session() as session:
            result = session.run(
                """
                MERGE (c:Concept {name: $name})
                SET c.description = COALESCE($description, c.description),
                    c.updated_at = datetime()
                RETURN c
                """,
                name=name,
                description=description
            )

            self.observability.record_knowledge_graph_operation("create_concept_node", "Concept")
            return dict(result.single()["c"])

    def create_agent_node(self, name: str, role: str = None, capabilities: List[str] = None) -> Dict:
        """Create an Agent node."""
        capabilities = capabilities or []

        with self.get_session() as session:
            result = session.run(
                """
                MERGE (a:Agent {name: $name})
                SET a.role = $role,
                    a.capabilities = $capabilities,
                    a.updated_at = datetime()
                RETURN a
                """,
                name=name,
                role=role,
                capabilities=capabilities
            )

            self.observability.record_knowledge_graph_operation("create_agent_node", "Agent")
            return dict(result.single()["a"])

    def store_memory(self, memory_id: int, content: str, concepts: List[str] = None) -> Dict:
        """
        Store a new memory node in the knowledge graph.
        """
        return self.create_memory_node(memory_id, content, concepts)

    # Relationship Creation Methods

    def _create_concept_relationship(self, session: Session, memory_id: int, concept: str):
        """Create relationship between Memory and Concept."""
        session.run(
            """
            MATCH (m:Memory {id: $memory_id})
            MERGE (c:Concept {name: $concept})
            SET c.updated_at = datetime()
            MERGE (m)-[r:MENTIONS]->(c)
            SET r.created_at = COALESCE(r.created_at, datetime())
            """,
            memory_id=memory_id,
            concept=concept
        )
        self.observability.record_knowledge_graph_operation("create_concept_relationship", "MENTIONS")

    def create_relationship(self, from_node: Dict, to_node: Dict, relationship_type: str, properties: Dict = None):
        """Create a relationship between two nodes."""
        properties = properties or {}

        with self.get_session() as session:
            # Determine node labels and identifiers
            from_label = list(from_node.keys())[0] if from_node else "Memory"
            to_label = list(to_node.keys())[0] if to_node else "Concept"

            query = f"""
            MATCH (from:{from_label} {{id: $from_id}})
            MATCH (to:{to_label} {{id: $to_id}})
            MERGE (from)-[r:{relationship_type}]->(to)
            SET r += $properties
            SET r.created_at = COALESCE(r.created_at, datetime())
            RETURN r
            """

            result = session.run(
                query,
                from_id=from_node.get("id"),
                to_id=to_node.get("id"),
                properties=properties
            )

            self.observability.record_knowledge_graph_operation("create_relationship", relationship_type)
            return dict(result.single()["r"]) if result.peek() else None

    # Query Methods

    def find_related_memories(self, memory_id: int, relationship_types: List[str] = None, limit: int = 10) -> List[Dict]:
        """Find memories related to the given memory through concepts."""
        relationship_types = relationship_types or ["MENTIONS"]

        with self.get_session() as session:
            result = session.run(
                """
                MATCH (m1:Memory {id: $memory_id})-[r1:MENTIONS]->(c:Concept)<-[r2:MENTIONS]-(m2:Memory)
                WHERE m1 <> m2
                RETURN DISTINCT m2, COUNT(c) as shared_concepts
                ORDER BY shared_concepts DESC
                LIMIT $limit
                """,
                memory_id=memory_id,
                limit=limit
            )

            return [{"memory": dict(record["m2"]), "shared_concepts": record["shared_concepts"]}
                   for record in result]

    def find_tools_by_concept(self, concept: str, limit: int = 5) -> List[Dict]:
        """Find tools related to a concept."""
        with self.get_session() as session:
            result = session.run(
                """
                MATCH (c:Concept {name: $concept})<-[:MENTIONS]-(m:Memory)-[:USES]->(t:Tool)
                RETURN DISTINCT t, COUNT(m) as usage_count
                ORDER BY usage_count DESC
                LIMIT $limit
                """,
                concept=concept,
                limit=limit
            )

            return [{"tool": dict(record["t"]), "usage_count": record["usage_count"]}
                   for record in result]

    def get_concept_network(self, concept: str, depth: int = 2) -> Dict:
        """Get the network of related concepts."""
        with self.get_session() as session:
            result = session.run(
                """
                MATCH path = (c1:Concept {name: $concept})-[*1..$depth]-(c2:Concept)
                RETURN path
                LIMIT 50
                """,
                concept=concept,
                depth=depth
            )

            nodes = set()
            relationships = []

            for record in result:
                path = record["path"]
                for node in path.nodes:
                    nodes.add((node.id, dict(node)))
                for rel in path.relationships:
                    relationships.append({
                        "start": rel.start_node.id,
                        "end": rel.end_node.id,
                        "type": rel.type,
                        "properties": dict(rel)
                    })

            return {
                "nodes": [{"id": node_id, "properties": props} for node_id, props in nodes],
                "relationships": relationships
            }

    def extract_concepts_from_content(self, content: str) -> List[str]:
        """Extract concepts from content using simple keyword extraction."""
        # This is a placeholder implementation
        # In production, you might use NLP libraries like spaCy, NLTK, or LLM APIs

        # Simple keyword extraction based on length and common patterns
        words = content.lower().split()
        concepts = []

        # Extract longer words (potential concepts)
        for word in words:
            if len(word) > 4 and word.isalpha():
                concepts.append(word.title())

        # Remove duplicates and return first 10
        return list(set(concepts))[:10]

    def run_cypher_query(self, query: str, parameters: Dict = None) -> List[Dict]:
        """Execute a raw Cypher query."""
        parameters = parameters or {}

        with self.get_session() as session:
            result = session.run(query, parameters)
            return [dict(record) for record in result]


# Global client instance
neo4j_client = None


def get_neo4j_client() -> Neo4jClient:
    """FastAPI dependency to get Neo4j client instance."""
    global neo4j_client
    if neo4j_client is None:
        neo4j_client = Neo4jClient()
    return neo4j_client


def close_neo4j_client():
    """Close the Neo4j client connection."""
    global neo4j_client
    if neo4j_client:
        neo4j_client.close()
        neo4j_client = None
