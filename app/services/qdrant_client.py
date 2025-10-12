import os
import uuid
from typing import Any, Dict, List, Optional

try:
    from qdrant_client import QdrantClient  # type: ignore
    from qdrant_client.http import models  # type: ignore
    from qdrant_client.http.models import Distance, PointStruct, VectorParams  # type: ignore
    _QDRANT_AVAILABLE = True
except Exception:
    # qdrant-client not installed in the test environment; provide stubs so imports succeed.
    QdrantClient = None  # type: ignore
    models = None  # type: ignore
    Distance = None  # type: ignore
    PointStruct = None  # type: ignore
    VectorParams = None  # type: ignore
    _QDRANT_AVAILABLE = False


class QdrantMemoryClient:
    """
    Qdrant client for memOS.as vector storage and semantic search.

    This client handles:
    - Creating and managing the "memories" collection
    - Storing vector embeddings with PostgreSQL memory IDs
    - Performing semantic search for memory retrieval
    """

    def __init__(self):
        self.host = os.environ.get("QDRANT_HOST", "localhost")
        self.port = int(os.environ.get("QDRANT_PORT", 6333))
        self.collection_name = "memories"
        # Initialize Qdrant client if package is available; otherwise create a stub
        if _QDRANT_AVAILABLE and QdrantClient is not None:
            try:
                self.client = QdrantClient(host=self.host, port=self.port)
                # Ensure collection exists
                self._ensure_collection_exists()
            except Exception as e:
                print(f"Warning: failed to initialize real Qdrant client: {e}")
                self.client = None
        else:
            # Running in a test environment without qdrant-client; use None and stub methods
            self.client = None

    def _ensure_collection_exists(self):
        """Create the memories collection if it doesn't exist"""
        if not self.client:
            # No-op in test environments
            return

        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [collection.name for collection in collections.collections]

            if self.collection_name not in collection_names:
                embedding_size = int(os.environ.get("EMBEDDING_SIZE", 384))

                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(size=embedding_size, distance=Distance.COSINE),
                )
                print(f"Created Qdrant collection '{self.collection_name}' with {embedding_size} dimensions")
            else:
                print(f"Qdrant collection '{self.collection_name}' already exists")

        except Exception as e:
            print(f"Error ensuring collection exists: {e}")

    def store_embedding(
        self,
        embedding: List[float],
        memory_id: int,
        agent_id: str = "default_agent",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Store a vector embedding with reference to PostgreSQL memory ID.

        Args:
            embedding: Vector embedding of the memory content
            memory_id: PostgreSQL memory ID for linking
            agent_id: The agent ID to associate with the memory
            metadata: Optional metadata to store with the vector

        Returns:
            Qdrant point ID if successful, None if failed
        """
        try:
            if not self.client:
                # No-op stub behavior for tests
                return str(uuid.uuid4())

            # Generate unique point ID
            point_id = str(uuid.uuid4())

            # Prepare payload with PostgreSQL memory ID and agent_id
            payload = {"memory_id": memory_id, "agent_id": agent_id, "metadata": metadata or {}}

            # Create point
            point = PointStruct(id=point_id, vector=embedding, payload=payload)

            # Store in Qdrant
            self.client.upsert(collection_name=self.collection_name, points=[point])

            return point_id

        except Exception as e:
            print(f"Error storing embedding: {e}")
            return None

    def search_similar_memories(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        score_threshold: float = 0.0,
        agent_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search to find similar memories.

        Args:
            query_embedding: Vector embedding of the query
            top_k: Number of similar memories to return
            score_threshold: Minimum similarity score threshold
            agent_id: Optional agent ID to filter memories

        Returns:
            List of search results with memory_ids and scores
        """
        try:
            if not self.client:
                return []

            query_filter = None
            if agent_id:
                query_filter = models.Filter(
                    must=[models.FieldCondition(key="agent_id", match=models.MatchValue(value=agent_id))]
                )

            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                query_filter=query_filter,
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True,
            )

            results = []
            for hit in search_result:
                results.append({
                    "memory_id": hit.payload.get("memory_id"),
                    "score": hit.score,
                    "point_id": hit.id,
                    "metadata": hit.payload.get("metadata", {}),
                })

            return results

        except Exception as e:
            print(f"Error searching similar memories: {e}")
            return []

    def get_embedding_by_memory_id(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """Get embedding info by PostgreSQL memory ID"""
        try:
            if not self.client:
                return None

            # Search by memory_id in payload
            search_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[models.FieldCondition(key="memory_id", match=models.MatchValue(value=memory_id))]
                ),
                limit=1,
                with_payload=True,
                with_vectors=True,
            )

            if search_result[0]:  # search_result is (points, next_page_offset)
                point = search_result[0][0]
                return {
                    "point_id": point.id,
                    "vector": point.vector,
                    "memory_id": point.payload.get("memory_id"),
                    "metadata": point.payload.get("metadata", {}),
                }

            return None

        except Exception as e:
            print(f"Error getting embedding by memory ID: {e}")
            return None

    def delete_embedding(self, point_id: str) -> bool:
        """Delete an embedding by point ID"""
        try:
            if not self.client:
                return True

            self.client.delete(collection_name=self.collection_name, points_selector=models.PointIdsList(points=[point_id]))
            return True

        except Exception as e:
            print(f"Error deleting embedding: {e}")
            return False

    def delete_embedding_by_memory_id(self, memory_id: int) -> bool:
        """Delete an embedding by PostgreSQL memory ID"""
        try:
            if not self.client:
                return True

            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[models.FieldCondition(key="memory_id", match=models.MatchValue(value=memory_id))]
                    )
                ),
            )
            return True

        except Exception as e:
            print(f"Error deleting embedding by memory ID: {e}")
            return False

    def get_collection_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the memories collection"""
        try:
            collection_info = self.client.get_collection(self.collection_name)
            return {
                "name": self.collection_name,
                "status": str(collection_info.status),
                "vectors_count": collection_info.vectors_count,
                "indexed_vectors_count": collection_info.indexed_vectors_count,
                "points_count": collection_info.points_count,
                "config": {
                    "distance": str(collection_info.config.params.vectors.distance),
                    "size": collection_info.config.params.vectors.size,
                },
            }

        except Exception as e:
            print(f"Error getting collection info: {e}")
            return None

    def generate_placeholder_embedding(self, text: str) -> List[float]:
        """
        Placeholder embedding function for development.
        In production, this should be replaced with actual embedding generation
        using models like sentence-transformers, OpenAI embeddings, etc.
        """
        # Simple hash-based placeholder (deterministic for testing)
        import hashlib

        # Get embedding size from environment or use default
        embedding_size = int(os.environ.get("EMBEDDING_SIZE", 384))

        # Create deterministic "embedding" based on text hash
        text_hash = hashlib.md5(text.encode()).hexdigest()

        # Convert hash to numbers and normalize
        embedding = []
        for i in range(embedding_size):
            # Use different parts of the hash to generate values
            hash_part = text_hash[
                (i * 2) % len(text_hash) : (i * 2 + 2) % len(text_hash)
            ]
            if not hash_part:
                hash_part = "00"

            # Convert to float between -1 and 1
            value = (int(hash_part, 16) / 255.0) * 2 - 1
            embedding.append(value)

        # Normalize the vector
        import math

        magnitude = math.sqrt(sum(x * x for x in embedding))
        if magnitude > 0:
            embedding = [x / magnitude for x in embedding]

        return embedding


# Global Qdrant client instance
qdrant_client = QdrantMemoryClient()


def get_qdrant_client() -> QdrantMemoryClient:
    """Get the global Qdrant client instance"""
    return qdrant_client
