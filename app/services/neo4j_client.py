"""
Neo4j client for memOS.as Tier 3 Knowledge Graph management.

This client handles:
- Connection management with Neo4j database
- Creating and managing graph nodes (Memory, Tool, Concept, Agent)
- Creating and querying relationships between entities
- Concept extraction and knowledge graph construction
"""

import os
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from neo4j import GraphDatabase, Driver, Session
from datetime import datetime


class Neo4jClient:
    """
    Neo4j client for Tier 3 Knowledge Graph operations.

    Manages conceptual relationships between memories, tools, concepts, and agents
    to provide higher-level understanding and context awareness.
    """

    def __init__(self):
        # In Docker compose networks the neo4j service is reachable at the hostname 'neo4j'.
        # Default to that so tests running inside containers can connect without extra env vars.
        """
        Initialize the Neo4j client configuration and an in-memory fallback store.
        
        Reads connection settings from environment variables and prepares the client without making a network connection. Environment variables considered:
        - NEO4J_URI: connection URI (defaults to "bolt://neo4j:7687").
        - NEO4J_AUTH: optional "user/password" pair (preferred if present).
        - NEO4J_USER or NEO4J_USERNAME: username fallback (defaults to "neo4j").
        - NEO4J_PASSWORD: password fallback (defaults to "apexsigma_neo4j_password").
        
        Sets:
        - self.uri (str): resolved connection URI.
        - self.username (str) and self.password (str): resolved credentials.
        - self.driver: initialized to None to enforce lazy connection attempts.
        - self._fallback (dict): in-memory store used when Neo4j is unavailable, with keys:
            - "memories": dict mapping memory_id -> memory dict
            - "tools": dict of tools
            - "concepts": dict of concepts
            - "agents": dict of agents
            - "relationships": list of relationship tuples/records for fallback operations
        """
        self.uri = os.environ.get("NEO4J_URI", "bolt://neo4j:7687")
        # Allow docker-compose to provide credentials via NEO4J_AUTH (format: user/password)
        neo4j_auth = os.environ.get("NEO4J_AUTH")
        if neo4j_auth and "/" in neo4j_auth:
            try:
                auth_user, auth_pass = neo4j_auth.split("/", 1)
                self.username = auth_user
                self.password = auth_pass
            except Exception:
                # Fall back to explicit env vars if parsing fails
                self.username = os.environ.get(
                    "NEO4J_USER", os.environ.get("NEO4J_USERNAME", "neo4j")
                )
                # Default password mirrors the one configured for the neo4j service in docker-compose
                self.password = os.environ.get("NEO4J_PASSWORD", "apexsigma_neo4j_password")
        else:
            self.username = os.environ.get(
                "NEO4J_USER", os.environ.get("NEO4J_USERNAME", "neo4j")
            )
            # Default password mirrors the one configured for the neo4j service in docker-compose
            self.password = os.environ.get("NEO4J_PASSWORD", "apexsigma_neo4j_password")

        # Do NOT connect at import time. Connection will be attempted lazily
        # when methods need it. This prevents test collection/import-time
        # failures when Neo4j isn't available in the environment.
        self.driver: Optional[Driver] = None

        # Simple in-memory fallback store used when Neo4j is unavailable.
        # This provides minimal behavior for unit tests that don't require
        # full Cypher capabilities.
        self._fallback: Dict[str, Any] = {
            "memories": {},  # memory_id -> memory dict
            "tools": {},
            "concepts": {},
            "agents": {},
            "relationships": [],  # list of (from_type, from_id, rel_type, to_type, to_id, properties)
        }

    def _connect(self):
        """Establish connection to Neo4j database with retry logic."""
        import time

        max_retries = 5
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                self.driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.username, self.password),
                    connection_timeout=10,  # 10 second timeout
                )
                # Test connection
                with self.driver.session() as session:
                    session.run("RETURN 1")
                print(f"✅ Connected to Neo4j at {self.uri}")
                return

            except Exception as e:
                if attempt < max_retries - 1:
                    print(
                        f"⚠️  Neo4j connection attempt {attempt + 1}/{max_retries} failed: {e}"
                    )
                    print(f"   Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print(
                        f"❌ Failed to connect to Neo4j after {max_retries} attempts: {e}"
                    )
                    print("💡 Ensure Neo4j is running: docker-compose up -d neo4j")
                    self.driver = None

        # If initial attempts failed and the configured URI looks like a docker service hostname
        # (for example 'bolt://neo4j:7687'), try a localhost fallback. This helps when running
        # tests on the host machine where Docker's internal DNS name 'neo4j' isn't resolvable.
        try:
            if self.driver is None and ("neo4j" in self.uri and "localhost" not in self.uri and "127.0.0.1" not in self.uri):
                local_uri = self.uri.replace("neo4j", "localhost")
                try:
                    print(f"ℹ️  Attempting localhost fallback to {local_uri}")
                    self.driver = GraphDatabase.driver(
                        local_uri,
                        auth=(self.username, self.password),
                        connection_timeout=10,
                    )
                    # Test connection
                    with self.driver.session() as session:
                        session.run("RETURN 1")
                    self.uri = local_uri
                    print(f"✅ Connected to Neo4j at {self.uri} (localhost fallback)")
                    return
                except Exception as e_local:
                    print(f"❌ Localhost fallback to {local_uri} failed: {e_local}")
                    self.driver = None
        except Exception:
            # Be defensive: any unexpected error here should not crash the caller
            pass

    def _is_connected(self) -> bool:
        """
        Check whether a Neo4j driver is currently available for use.
        
        Returns:
            bool: `True` if the client has an initialized Neo4j driver, `False` otherwise.
        """
        return self.driver is not None

    def _create_constraints(self):
        """
        Create uniqueness constraints for core node types (Memory, Tool, Concept, Agent).
        
        If the client is not connected to a Neo4j driver, this is a no-op. Attempts to create the constraints are executed against the database and any errors (for example, constraints that already exist) are suppressed.
        """
        if not self.driver:
            return

        constraints = [
            "CREATE CONSTRAINT memory_id_unique IF NOT EXISTS FOR (m:Memory) REQUIRE m.id IS UNIQUE",
            "CREATE CONSTRAINT tool_name_unique IF NOT EXISTS FOR (t:Tool) REQUIRE t.name IS UNIQUE",
            "CREATE CONSTRAINT concept_name_unique IF NOT EXISTS FOR (c:Concept) REQUIRE c.name IS UNIQUE",
            "CREATE CONSTRAINT agent_name_unique IF NOT EXISTS FOR (a:Agent) REQUIRE a.name IS UNIQUE",
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
        """
        Provide a context manager that yields a Neo4j session when connected or `None` when the client is operating in fallback (in-memory) mode.
        
        Yields:
            session (neo4j.Session | None): A live Neo4j session if the client is connected; `None` to signal callers should use the in-memory fallback store.
        """
        # If there's no live driver, yield None to indicate callers should
        # fall back to the in-memory store. This avoids raising at import
        # time and lets tests execute without a running Neo4j instance.
        if not self._is_connected():
            yield None
            return

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

    def create_memory_node(
        self, memory_id: int, content: str, concepts: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a Memory node and associate it with the given concepts.
        
        When Neo4j is connected, creates a Memory node in the database and links it to each concept in `concepts`. When running in fallback mode (Neo4j unavailable), stores an equivalent memory record in the in-memory store and records MENTIONS relationships.
        
        Parameters:
            memory_id (int): Unique identifier for the memory.
            content (str): Text content of the memory.
            concepts (Optional[List[str]]): List of concept names to associate with the memory.
        
        Returns:
            Dict[str, Any]: A dictionary representation of the created Memory node (database node properties when connected, or the in-memory record when using the fallback).
        """
        concepts = concepts or []
        # If Neo4j is available, use it. Otherwise use the in-memory fallback.
        if self._is_connected():
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
                    content=content,
                )

                memory_node = result.single()["m"]

                # Create concept nodes and relationships
                for concept in concepts:
                    self._create_concept_relationship(session, memory_id, concept)

                return dict(memory_node)

        # Fallback: store in-memory
        now = datetime.utcnow().isoformat()
        memory_node = {
            "id": memory_id,
            "content": content,
            "created_at": now,
            "updated_at": now,
            "concepts": list(concepts),
        }
        self._fallback["memories"][memory_id] = memory_node
        # link concepts in fallback store
        for concept in concepts:
            self._fallback["concepts"].setdefault(concept, {"name": concept})
            self._fallback["relationships"].append(
                ("Memory", memory_id, "MENTIONS", "Concept", concept, {})
            )

        return memory_node

    def create_tool_node(
        self, name: str, description: str, usage: str, tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create or update a Tool node with the given metadata and return its representation.
        
        Parameters:
            name (str): Unique tool name.
            description (str): Human-readable description of the tool.
            usage (str): Short usage notes or instructions.
            tags (List[str], optional): List of tag strings associated with the tool.
        
        Returns:
            Dict[str, Any]: When connected to Neo4j, a dict representing the created/merged Tool node (node properties).
            In fallback mode, a plain dict with keys "name", "description", "usage", and "tags" representing the stored tool.
        """
        tags = tags or []
        if self._is_connected():
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
                    tags=tags,
                )

                return dict(result.single()["t"])

        # Fallback
        tool = {"name": name, "description": description, "usage": usage, "tags": tags}
        self._fallback["tools"][name] = tool
        return tool

    def create_concept_node(self, name: str, description: Optional[str] = None) -> Dict[str, Any]:
        """
        Create or update a Concept node and return its properties.
        
        Returns:
            Dict[str, Any]: The concept node properties; when connected to Neo4j this is the node record converted to a dict, otherwise an in-memory dict with keys like `name` and `description`.
        """
        if self._is_connected():
            with self.get_session() as session:
                result = session.run(
                    """
                    MERGE (c:Concept {name: $name})
                    SET c.description = COALESCE($description, c.description),
                        c.updated_at = datetime()
                    RETURN c
                    """,
                    name=name,
                    description=description,
                )

                return dict(result.single()["c"])

        concept = {"name": name, "description": description}
        self._fallback["concepts"][name] = concept
        return concept

    def create_agent_node(
        self, name: str, role: Optional[str] = None, capabilities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create or update an Agent node in the graph and return its properties.
        
        If Neo4j is connected, merges an Agent node by `name`, updates `role`, `capabilities`, and sets `updated_at`, then returns the node's properties as a dict. If Neo4j is not connected, stores and returns a plain dict in the in-memory fallback.
        
        Parameters:
            name (str): Agent name used as the unique identifier.
            role (Optional[str]): Optional role assigned to the agent.
            capabilities (Optional[List[str]]): Optional list of capabilities; defaults to an empty list when not provided.
        
        Returns:
            Dict[str, Any]: A dictionary of the agent's properties. When persisted to Neo4j this will include `updated_at`; the fallback path returns a dict with `name`, `role`, and `capabilities`.
        """
        capabilities = capabilities or []
        if self._is_connected():
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
                    capabilities=capabilities,
                )

                return dict(result.single()["a"])

        agent = {"name": name, "role": role, "capabilities": capabilities}
        self._fallback["agents"][name] = agent
        return agent

    def store_memory(
        self, memory_id: int, content: str, concepts: List[str] = None
    ) -> Dict:
        """
        Create and persist a memory node in the knowledge graph (or in-memory fallback) and associate it with optional concepts.
        
        Parameters:
            memory_id (int): Unique identifier for the memory.
            content (str): Text content of the memory.
            concepts (List[str], optional): List of concept names to link to the memory.
        
        Returns:
            dict: Representation of the created memory node (includes at least `id`, `content`, `created_at`, and `updated_at`; may include concept relationships).
        """
        return self.create_memory_node(memory_id, content, concepts)

    # Relationship Creation Methods

    def _create_concept_relationship(
        self, session: Session, memory_id: int, concept: str
    ):
        """
        Create or record a MENTIONS relationship between a Memory and a Concept.
        
        When connected to Neo4j (a valid Session), ensures a Concept node exists, updates its timestamp, and creates/merges a MENTIONS relationship from the Memory node with creation timestamp. If `session` is None or the client is not connected, records the concept and relationship in the in-memory fallback store.
        
        Parameters:
            session (neo4j.Session | None): Active Neo4j session, or `None` to use the in-memory fallback.
            memory_id (int): Identifier of the Memory node.
            concept (str): Name of the Concept to relate to the Memory.
        """
        # If session is None, we're in fallback mode.
        if session is None or not self._is_connected():
            # ensure concept exists
            self._fallback["concepts"].setdefault(concept, {"name": concept})
            # record the relationship
            self._fallback["relationships"].append(
                ("Memory", memory_id, "MENTIONS", "Concept", concept, {})
            )
            return

        session.run(
            """
            MATCH (m:Memory {id: $memory_id})
            MERGE (c:Concept {name: $concept})
            SET c.updated_at = datetime()
            MERGE (m)-[r:MENTIONS]->(c)
            SET r.created_at = COALESCE(r.created_at, datetime())
            """,
            memory_id=memory_id,
            concept=concept,
        )

    def create_relationship(
        self,
        from_node: Dict,
        to_node: Dict,
        relationship_type: str,
        properties: Dict = None,
    ):
        """
        Create or merge a relationship of the given type between two nodes.
        
        If the client is connected to Neo4j, ensures a relationship of `relationship_type` exists between the node identified by `from_node` and the node identified by `to_node`, merges provided `properties` into the relationship, and returns the stored relationship properties as a dict (or `None` if no relationship was returned). When Neo4j is not available, records the relationship in the in-memory fallback store and returns a dict with keys `from`, `to`, `type`, and `properties`.
        
        Parameters:
            from_node (dict): A mapping representing the source node. Expected to contain an `id` key and either a `label` key or a single top-level label key mapping to the node properties.
            to_node (dict): A mapping representing the target node. Expected to contain an `id` key and either a `label` key or a single top-level label key mapping to the node properties.
            relationship_type (str): The relationship type/name to create or merge (e.g., "MENTIONS").
            properties (dict, optional): Properties to set or merge on the relationship.
        
        Returns:
            dict or None: In fallback mode, a dict with keys `from`, `to`, `type`, and `properties`. When connected to Neo4j, a dict of the relationship's stored properties if available, or `None`.
        """
        properties = properties or {}

        properties = properties or {}

        # Fallback behavior when Neo4j is not available
        if not self._is_connected():
            from_label = from_node.get("label") if isinstance(from_node, dict) else None
            from_id = from_node.get("id") if isinstance(from_node, dict) else None
            to_label = to_node.get("label") if isinstance(to_node, dict) else None
            to_id = to_node.get("id") if isinstance(to_node, dict) else None
            self._fallback["relationships"].append(
                (from_label or "Unknown", from_id, relationship_type, to_label or "Unknown", to_id, properties)
            )
            return {"from": from_id, "to": to_id, "type": relationship_type, "properties": properties}

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
                properties=properties,
            )

            return dict(result.single()["r"]) if result.peek() else None

    # Query Methods

    def find_related_memories(
        self,
        memory_id: int,
        relationship_types: Optional[List[str]] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Find memories that share concepts with the specified memory.
        
        Searches for other Memory nodes that mention the same Concept(s) as the memory identified by memory_id. When a Neo4j driver is available this runs a Cypher query that counts shared concepts; when Neo4j is unavailable it performs an equivalent search against the in-memory fallback store.
        
        Parameters:
            memory_id (int): Identifier of the source memory to find related memories for.
            relationship_types (Optional[List[str]]): Relationship types to consider when traversing (defaults to ["MENTIONS"]).
            limit (int): Maximum number of related memories to return.
        
        Returns:
            List[Dict[str, Any]]: A list of results ordered by descending shared concept count. Each item is a dict with:
                - "memory": the related memory node as a dict of properties
                - "shared_concepts": the number of concepts shared with the source memory
        """
        relationship_types = relationship_types or ["MENTIONS"]

        if not self._is_connected():
            # Naive fallback: find other memories that mention the same concepts
            target = self._fallback["memories"].get(memory_id)
            if not target:
                return []
            target_concepts = set(target.get("concepts", []))
            results = []
            for mid, mem in self._fallback["memories"].items():
                if mid == memory_id:
                    continue
                shared = target_concepts.intersection(set(mem.get("concepts", [])))
                if shared:
                    results.append({"memory": mem, "shared_concepts": len(shared)})
            # sort
            results.sort(key=lambda r: r["shared_concepts"], reverse=True)
            return results[:limit]

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
                limit=limit,
            )

            return [
                {
                    "memory": dict(record["m2"]),
                    "shared_concepts": record["shared_concepts"],
                }
                for record in result
            ]

    def find_tools_by_concept(self, concept: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find tools associated with the given concept, ranked by how many memories reference them.
        
        Parameters:
            concept (str): Name of the Concept to search for.
            limit (int): Maximum number of tools to return.
        
        Returns:
            List[Dict[str, Any]]: List of items where each item contains:
                - "tool": a dict of the tool's properties
                - "usage_count": int count of distinct memories that reference the tool
        """
        if not self._is_connected():
            # Basic fallback: return tools referenced by memories that mention the concept
            tools = {}
            for rel in self._fallback["relationships"]:
                f_type, f_id, rel_type, t_type, t_id, props = rel
                if rel_type == "MENTIONS" and t_type == "Concept" and t_id == concept:
                    # find memories that mention the concept
                    mem = self._fallback["memories"].get(f_id)
                    if not mem:
                        continue
                    # find any relationships from this memory to tools
                    for r in self._fallback["relationships"]:
                        if r[0] == "Memory" and r[1] == f_id and r[2] == "USES" and r[3] == "Tool":
                            tool_id = r[4]
                            tools.setdefault(tool_id, 0)
                            tools[tool_id] += 1
            items = []
            for tid, count in sorted(tools.items(), key=lambda x: x[1], reverse=True)[:limit]:
                items.append({"tool": self._fallback["tools"].get(tid, {}), "usage_count": count})
            return items

        with self.get_session() as session:
            result = session.run(
                """
                MATCH (c:Concept {name: $concept})<-[:MENTIONS]-(m:Memory)-[:USES]->(t:Tool)
                RETURN DISTINCT t, COUNT(m) as usage_count
                ORDER BY usage_count DESC
                LIMIT $limit
                """,
                concept=concept,
                limit=limit,
            )

            return [
                {
                    "tool": dict(record["t"]),
                    "usage_count": record["usage_count"],
                }
                for record in result
            ]

    def get_concept_network(self, concept: str, depth: int = 2) -> Dict[str, Any]:
        """
        Return the concept graph around a given concept up to a specified depth.
        
        Parameters:
            concept (str): The starting Concept name to expand.
            depth (int): Maximum number of relationship hops to traverse from the starting concept.
        
        Returns:
            Dict[str, Any]: A dictionary with keys "nodes" and "relationships".
                "nodes" is a list of objects with "id" and "properties".
                "relationships" is a list of objects with "start", "end", "type", and "properties".
        """
        if not self._is_connected():
            # Fallback: return nodes that are concepts and relationships that mention them
            nodes = []
            relationships = []
            for name, c in self._fallback["concepts"].items():
                nodes.append({"id": name, "properties": c})
            for rel in self._fallback["relationships"]:
                start, start_id, rtype, end, end_id, props = rel
                if start == "Concept" or end == "Concept":
                    relationships.append({"start": start_id, "end": end_id, "type": rtype, "properties": props})
            return {"nodes": nodes, "relationships": relationships}

        with self.get_session() as session:
            result = session.run(
                """
                MATCH path = (c1:Concept {name: $concept})-[*1..$depth]-(c2:Concept)
                RETURN path
                LIMIT 50
                """,
                concept=concept,
                depth=depth,
            )

            return self._format_graph_output(result)

    def get_related_nodes(self, node_id: str) -> Dict[str, Any]:
        """
        Return the subgraph consisting of the given node and all nodes directly connected to it, including the connecting relationships.
        
        Returns:
            graph (Dict[str, Any]): A dictionary with keys:
                - "nodes": List of node dictionaries, each with "id" and "properties".
                - "relationships": List of relationship dictionaries, each with "start", "end", "type", and "properties".
        """
        if not self._is_connected():
            nodes = []
            relationships = []
            for mid, mem in self._fallback["memories"].items():
                if mid == node_id:
                    nodes.append({"id": mid, "properties": mem})
            for rel in self._fallback["relationships"]:
                start, start_id, rtype, end, end_id, props = rel
                if start_id == node_id or end_id == node_id:
                    relationships.append({"start": start_id, "end": end_id, "type": rtype, "properties": props})
            return {"nodes": nodes, "relationships": relationships}

        with self.get_session() as session:
            result = session.run(
                """
                MATCH (n) WHERE n.id = $node_id
                MATCH (n)-[r]-(m)
                RETURN n, r, m
                """,
                node_id=node_id,
            )
            return self._format_graph_output(result)

    def get_shortest_path(self, start_node_id: str, end_node_id: str) -> Dict[str, Any]:
        """
        Finds the shortest path between two nodes in the knowledge graph.
        
        Returns:
            dict: A mapping with keys "nodes" and "relationships". "nodes" is a list of node dictionaries representing the nodes along the shortest path; "relationships" is a list of relationship dictionaries each containing "start", "end", "type", and "properties". If Neo4j is unavailable, returns any direct relationships between the two node ids and an empty "nodes" list.
        """
        if not self._is_connected():
            # Very naive fallback: if direct relationships exist between the two ids, return them
            rels = []
            for rel in self._fallback["relationships"]:
                start, start_id, rtype, end, end_id, props = rel
                if (start_id == start_node_id and end_id == end_node_id) or (start_id == end_node_id and end_id == start_node_id):
                    rels.append(rel)
            return {"nodes": [], "relationships": [
                {"start": r[1], "end": r[4], "type": r[2], "properties": r[5]} for r in rels
            ]}

        with self.get_session() as session:
            result = session.run(
                """
                MATCH (start), (end)
                WHERE start.id = $start_node_id AND end.id = $end_node_id
                CALL apoc.path.shortestPath(start, end, null, 10)
                YIELD path
                RETURN path
                """,
                start_node_id=start_node_id,
                end_node_id=end_node_id,
            )
            return self._format_graph_output(result)

    def get_subgraph(self, node_id: str, depth: int = 1) -> Dict[str, Any]:
        """
        Return the subgraph centered on the specified node up to the given depth.
        
        Searches for nodes and relationships reachable from the node identified by `node_id` up to `depth` hops. When a Neo4j connection is available the result is obtained from the database (APOC subgraphAll); when Neo4j is unavailable the method returns an in-memory fallback representation.
        
        Parameters:
            node_id (str): Identifier of the central node.
            depth (int): Maximum path length (number of hops) to include; defaults to 1.
        
        Returns:
            Dict[str, Any]: A dictionary with keys:
                - "nodes": list of node dictionaries, each containing "id" and "properties".
                - "relationships": list of relationship dictionaries, each containing "start", "end", "type", and "properties".
        """
        if not self._is_connected():
            nodes = []
            relationships = []
            for rel in self._fallback["relationships"]:
                start, start_id, rtype, end, end_id, props = rel
                if start_id == node_id or end_id == node_id:
                    relationships.append({"start": start_id, "end": end_id, "type": rtype, "properties": props})
            if node_id in self._fallback["memories"]:
                nodes.append({"id": node_id, "properties": self._fallback["memories"][node_id]})
            return {"nodes": nodes, "relationships": relationships}

        with self.get_session() as session:
            result = session.run(
                """
                MATCH (n) WHERE n.id = $node_id
                CALL apoc.path.subgraphAll(n, {maxLevel: $depth})
                YIELD nodes, relationships
                RETURN nodes, relationships
                """,
                node_id=node_id,
                depth=depth,
            )
            return self._format_graph_output(result)

    def extract_concepts_from_content(self, content: str) -> List[str]:
        """
        Extracts potential concept keywords from a text string using a simple heuristic.
        
        Parameters:
            content: Text to extract concepts from.
        
        Returns:
            A list of extracted concept candidates (capitalized). Duplicates are removed and the list is limited to at most 10 items.
        """
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

    def run_cypher_query(self, query: str, parameters: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Execute a raw Cypher query against the connected Neo4j database.
        
        Parameters:
            query (str): Cypher query string to execute.
            parameters (Optional[Dict]): Mapping of parameter names to values for the query.
        
        Returns:
            List[Dict[str, Any]]: A list of result records where each record is converted to a dict of keys to values.
        
        Raises:
            NotImplementedError: If Neo4j is unavailable and the in-memory fallback is active (raw Cypher not supported).
        """
        parameters = parameters or {}
        if not self._is_connected():
            # Raw Cypher is not supported by the fallback store.
            raise NotImplementedError("Cypher queries are not supported when Neo4j is unavailable (fallback mode).")

        with self.get_session() as session:
            result = session.run(query, parameters)
            return [dict(record) for record in result]

    def _format_graph_output(self, result) -> Dict:
        """Helper function to format graph query results."""
        nodes = set()
        relationships = []

        for record in result:
            if "path" in record:
                path = record["path"]
                for node in path.nodes:
                    nodes.add((node.id, dict(node)))
                for rel in path.relationships:
                    relationships.append(
                        {
                            "start": rel.start_node.id,
                            "end": rel.end_node.id,
                            "type": rel.type,
                            "properties": dict(rel),
                        }
                    )
            else:
                if "n" in record:
                    node_n = record["n"]
                    nodes.add((node_n.id, dict(node_n)))
                if "m" in record:
                    node_m = record["m"]
                    nodes.add((node_m.id, dict(node_m)))
                if "r" in record:
                    rel = record["r"]
                    relationships.append(
                        {
                            "start": rel.start_node.id,
                            "end": rel.end_node.id,
                            "type": rel.type,
                            "properties": dict(rel),
                        }
                    )
                if "nodes" in record and "relationships" in record:
                    for node in record["nodes"]:
                        nodes.add((node.id, dict(node)))
                    for rel in record["relationships"]:
                        relationships.append(
                            {
                                "start": rel.start_node.id,
                                "end": rel.end_node.id,
                                "type": rel.type,
                                "properties": dict(rel),
                            }
                        )

        return {
            "nodes": [{"id": node_id, "properties": props} for node_id, props in nodes],
            "relationships": relationships,
        }


# Global client instance
neo4j_client = None


def get_neo4j_client() -> Neo4jClient:
    """
    Return a shared Neo4jClient singleton, creating and initializing it on first use.
    
    On first call this function instantiates the global Neo4jClient, attempts to establish a driver connection and create database constraints, and falls back to the in-memory store if connection or constraint setup fails (exceptions are swallowed). Subsequent calls return the same client instance.
    
    Returns:
        Neo4jClient: The global Neo4jClient instance (may be operating in fallback/in-memory mode if a live Neo4j connection could not be established).
    """
    global neo4j_client
    if neo4j_client is None:
        neo4j_client = Neo4jClient()
        # Attempt to connect now (lazy) so tests that expect a live driver
        # can assert on neo4j_client.driver. If the connection fails, the
        # client remains in fallback mode but tests will still be able to
        # use the in-memory behavior.
        try:
            neo4j_client._connect()
            neo4j_client._create_constraints()
        except Exception:
            # Swallow exceptions; fallback store is available for tests.
            pass
    return neo4j_client


def close_neo4j_client():
    """Close the Neo4j client connection."""
    global neo4j_client
    if neo4j_client:
        neo4j_client.close()
        neo4j_client = None