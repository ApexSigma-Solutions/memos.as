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
        Initialize client configuration from environment variables and prepare an in-memory fallback store.
        
        Reads connection settings from environment variables: NEO4J_URI (default "bolt://neo4j:7687"), NEO4J_AUTH (optional "user/password" form), or NEO4J_USER / NEO4J_USERNAME and NEO4J_PASSWORD with sensible defaults. Does not open a network connection at construction time; the Neo4j driver is left None for lazy connection attempts. Creates a minimal in-memory fallback store under self._fallback with keys:
        - "memories": mapping of memory_id -> memory dict
        - "tools": mapping of tool name/id -> tool dict
        - "concepts": mapping of concept name -> concept dict
        - "agents": mapping of agent name -> agent dict
        - "relationships": list of recorded relationships (tuples or dicts describing from, to, type, properties)
        
        This enables the client to operate in a limited offline mode when a Neo4j instance is unavailable.
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
        """
        Attempt to establish and verify a Neo4j driver connection for this client.
        
        Tries to create and test a GraphDatabase driver, updating self.driver on success.
        On repeated failures the method leaves self.driver as None, performs a localhost
        fallback when the configured URI appears to reference a Docker service hostname
        (e.g., replacing 'neo4j' with 'localhost'), and updates self.uri if the fallback
        succeeds. Connection attempts and outcomes are reported via stdout.
        """
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
        Check whether a Neo4j driver is configured and available.
        
        Returns:
            True if a Neo4j driver is configured (connection established), False otherwise.
        """
        return self.driver is not None

    def _create_constraints(self):
        """
        Ensure uniqueness constraints exist for core node labels in the connected Neo4j database.
        
        Creates uniqueness constraints for:
        - Memory.id
        - Tool.name
        - Concept.name
        - Agent.name
        
        If the client is not connected to Neo4j this method is a no-op. Existing constraints are ignored without raising.
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
        Provide a context manager that yields a Neo4j session or `None` when Neo4j is unavailable.
        
        When the client is connected, yields an active Neo4j session and ensures the session is closed on exit. When not connected, yields `None` to signal callers to use the in-memory fallback store.
        
        Returns:
            session (neo4j.Session | None): An active Neo4j session if connected, `None` otherwise.
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
        Create a Memory node and associate it with the provided concepts.
        
        Creates a memory record with the given id and content, and links the memory to each name in `concepts`. In environments without a Neo4j backend this populates the local in-memory fallback store; in either case the function returns a dictionary representation of the created memory node.
        
        Parameters:
            memory_id (int): Unique identifier for the memory.
            content (str): Text content of the memory.
            concepts (Optional[List[str]]): List of concept names to associate with the memory.
        
        Returns:
            Dict[str, Any]: Dictionary representing the created memory node with keys including
            `id`, `content`, `created_at`, `updated_at`, and `concepts` (list of associated concept names).
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
        Create or update a Tool node in the knowledge graph or in the in-memory fallback.
        
        Parameters:
            name (str): Tool name used as the unique identifier.
            description (str): Human-readable description of the tool.
            usage (str): Example or explanation of how the tool is used.
            tags (Optional[List[str]]): Optional list of tag strings associated with the tool.
        
        Returns:
            Dict[str, Any]: The tool node properties (e.g., name, description, usage, tags, and updated timestamps when available).
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
        Create or update a Concept node identified by name and optionally set its description.
        
        Parameters:
            name (str): The unique name of the concept.
            description (Optional[str]): An optional textual description to set or update for the concept.
        
        Returns:
            Dict[str, Any]: A dictionary of the concept's properties. When connected to Neo4j this contains the node properties (e.g., `name`, `description`, `updated_at`); when running in fallback mode this is a stored dict with `name` and `description`.
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
        Create or update an Agent node in the knowledge graph.
        
        When connected to Neo4j, merges an Agent node with the given properties and returns the node's properties as a dict (including `updated_at` when present). When Neo4j is unavailable, stores and returns an in-memory agent dict.
        
        Parameters:
            name (str): Unique agent name.
            role (Optional[str]): Optional role or description of the agent.
            capabilities (Optional[List[str]]): Optional list of capability strings.
        
        Returns:
            dict: Agent properties (e.g., `name`, `role`, `capabilities`, and `updated_at` when present).
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
        Store a new memory node in the knowledge graph.
        """
        return self.create_memory_node(memory_id, content, concepts)

    # Relationship Creation Methods

    def _create_concept_relationship(
        self, session: Session, memory_id: int, concept: str
    ):
        """
        Create or ensure a Concept node and a MENTIONS relationship from a Memory node to that Concept.
        
        When connected to Neo4j, ensures the Concept exists (creating it if missing), updates its timestamp, and creates the MENTIONS relationship from the Memory identified by `memory_id` to that Concept, setting relationship timestamps as needed. If `session` is None or the client is not connected, record the concept and the MENTIONS relationship in the in-memory fallback store instead.
        
        Parameters:
            session (neo4j.Session | None): Active Neo4j session to use; pass `None` to operate on the in-memory fallback.
            memory_id (int): Identifier of the Memory node that mentions the concept.
            concept (str): Name of the Concept to create or link.
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
        Create a relationship between two nodes in the graph.
        
        Parameters:
            from_node (dict): Representation of the source node. Should include an `id` and optionally a `label`.
            to_node (dict): Representation of the target node. Should include an `id` and optionally a `label`.
            relationship_type (str): Type/name of the relationship to create.
            properties (dict, optional): Properties to set on the relationship.
        
        Returns:
            dict or None: When the operation records the relationship in the fallback store, returns a dict with keys
            `from`, `to`, `type`, and `properties`. When executed against Neo4j, returns a dict of the relationship's
            properties if a relationship was created or merged, or `None` if no relationship was produced.
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
        
        Parameters:
            memory_id (int): ID of the memory to find related memories for.
            relationship_types (Optional[List[str]]): Relationship types to consider when determining relatedness (defaults to ["MENTIONS"]).
            limit (int): Maximum number of related memories to return.
        
        Returns:
            List[Dict[str, Any]]: A list of objects each containing:
                - `memory` (dict): The related memory's properties.
                - `shared_concepts` (int): Number of concepts shared with the target memory.
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
        Retrieve tools associated with a concept, ordered by how many memories reference them.
        
        Parameters:
        	concept (str): Concept name to search for.
        	limit (int): Maximum number of tools to return (ordered by usage count).
        
        Returns:
        	List[Dict[str, Any]]: A list of objects each containing:
        		- `tool` (dict): The tool node's properties.
        		- `usage_count` (int): Number of distinct memories that reference the tool, ordered descending.
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
        Retrieve a subgraph of Concept nodes connected to the given concept up to a specified depth.
        
        Parameters:
        	concept (str): Name of the starting Concept node.
        	depth (int): Maximum path length to traverse from the starting concept (1 or greater).
        
        Returns:
        	graph (dict): Dictionary with two keys:
        		- nodes (List[dict]): Each node as {"id": <node_identifier>, "properties": <properties_dict>}.
        		- relationships (List[dict]): Each relationship as {"start": <start_id>, "end": <end_id>, "type": <rel_type>, "properties": <properties_dict>}.
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
        Retrieve the node with the given id and its directly connected nodes and relationships.
        
        When Neo4j is unavailable, returns the same structure derived from the in-memory fallback store.
        
        Returns:
            graph (dict): A mapping with two keys:
                - nodes (List[dict]): Each dict has `id` (node identifier) and `properties` (node properties).
                - relationships (List[dict]): Each dict has `start` (start node id), `end` (end node id), `type` (relationship type), and `properties` (relationship properties).
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
        Finds the shortest path between two nodes in the graph.
        
        When connected to Neo4j, uses APOC's shortestPath (limited to length 10) and returns the path formatted as nodes and relationships. When not connected, returns a naive fallback containing any directly recorded relationships between the two node ids.
        
        Parameters:
            start_node_id (str): Identifier of the start node.
            end_node_id (str): Identifier of the end node.
        
        Returns:
            dict: A graph representation with keys:
                - nodes (list): List of node dictionaries (each includes an `id` and `properties`) present on the path.
                - relationships (list): List of relationship dictionaries with keys:
                    - start (str): start node id
                    - end (str): end node id
                    - type (str): relationship type
                    - properties (dict): relationship properties
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
        Get the subgraph around a node up to a specified traversal depth.
        
        When connected to Neo4j this returns the neighborhood discovered by APOC's subgraph traversal; when running in fallback mode this returns any stored nodes and relationships that reference the node.
        
        Parameters:
            node_id (str): Identifier of the central node to expand.
            depth (int): Maximum traversal depth from the central node (0 includes only the node).
        
        Returns:
            dict: A mapping with keys:
                - nodes: list of node objects each with `id` and `properties`.
                - relationships: list of relationship objects each with `start`, `end`, `type`, and `properties`.
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
        Extract a short list of candidate concept tokens found in the provided text.
        
        This uses a lightweight heuristic: selects alphabetic words longer than four characters, converts them to title case, removes duplicates, and returns up to 10 items.
        
        Parameters:
            content (str): Text to extract concepts from.
        
        Returns:
            List[str]: Up to 10 unique candidate concept strings (title-cased).
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
        Run a raw Cypher query against the connected Neo4j database.
        
        Returns:
            A list of records, each represented as a dict mapping field names to their values.
        
        Raises:
            NotImplementedError: If Neo4j is unavailable and the fallback in-memory store is being used.
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
    Provide the module-wide Neo4jClient singleton for dependency injection.
    
    Returns:
        neo4j_client (Neo4jClient): The shared Neo4jClient instance. If a real Neo4j connection could not be established during initialization, the returned client remains usable in fallback (in-memory) mode.
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