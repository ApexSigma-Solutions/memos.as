import os
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.http import models
from qdrant_client.http.models import Distance, PointStruct, VectorParams

from app.services.observability import get_observability


class QdrantMemoryClient:
    """
    Qdrant client for memOS.as vector storage and semantic search.

    This client handles:
    - Creating and managing the "memories" collection
    - Storing vector embeddings with PostgreSQL memory IDs
    - Performing semantic search for memory retrieval
    """

    def __init__(self):
        self.observability = get_observability()
        self.host = os.environ.get("QDRANT_HOST", "devenviro_qdrant")
        self.port = int(os.environ.get("QDRANT_PORT", 6333))
        self.collection_name = "memories"

        # Initialize Qdrant client
        self.client = QdrantClient(host=self.host, port=self.port)

        # Ensure collection exists
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Create the memories collection if it doesn't exist"""
        try:
            # Check if collection exists
            collections = self.client.get_collections()
            collection_names = [
                collection.name for collection in collections.collections
            ]

            if self.collection_name not in collection_names:
                # Create collection with default embedding size (can be adjusted)
                # Using 384 dimensions for sentence-transformers/all-MiniLM-L6-v2
                # This can be configured via environment variable
                embedding_size = int(os.environ.get("EMBEDDING_SIZE", 384))

                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=embedding_size, distance=Distance.COSINE
                    ),
                )
                self.observability.log_structured(
                    "info",
                    "Qdrant collection created",
                    collection_name=self.collection_name,
                    embedding_size=embedding_size,
                )
            else:
                self.observability.log_structured(
                    "info",
                    "Qdrant collection already exists",
                    collection_name=self.collection_name,
                )

        except Exception as e:
            self.observability.log_structured(
                "error", "Error ensuring Qdrant collection exists", error=str(e)
            )

    def store_embedding(
        self,
        embedding: List[float],
        memory_id: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """
        Store a vector embedding with reference to PostgreSQL memory ID.
        """
        try:
            # Generate unique point ID
            point_id = str(uuid.uuid4())

            # Prepare payload with PostgreSQL memory ID
            payload = {"memory_id": memory_id, "metadata": metadata or {}}

            # Create point
            point = PointStruct(id=point_id, vector=embedding, payload=payload)

            # Store in Qdrant
            self.client.upsert(collection_name=self.collection_name, points=[point])
            self.observability.record_memory_operation("qdrant_store", "success", "tier2")
            return point_id

        except Exception as e:
            self.observability.record_memory_operation("qdrant_store", "failed", "tier2")
            self.observability.log_structured(
                "error", "Error storing embedding in Qdrant", error=str(e)
            )
            return None

    def search_similar_memories(
        self, query_embedding: List[float], top_k: int = 5, score_threshold: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Perform semantic search to find similar memories.
        """
        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding,
                limit=top_k,
                score_threshold=score_threshold,
                with_payload=True,
            )

            results = []
            for hit in search_result:
                results.append(
                    {
                        "memory_id": hit.payload.get("memory_id"),
                        "score": hit.score,
                        "point_id": hit.id,
                        "metadata": hit.payload.get("metadata", {}),
                    }
                )
            self.observability.record_memory_operation("qdrant_search", "success", "tier2")
            return results

        except Exception as e:
            self.observability.record_memory_operation("qdrant_search", "failed", "tier2")
            self.observability.log_structured(
                "error", "Error searching similar memories in Qdrant", error=str(e)
            )
            return []

    def get_embedding_by_memory_id(self, memory_id: int) -> Optional[Dict[str, Any]]:
        """Get embedding info by PostgreSQL memory ID"""
        try:
            # Search by memory_id in payload
            search_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="memory_id", match=models.MatchValue(value=memory_id)
                        )
                    ]
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
            self.observability.log_structured(
                "error", "Error getting embedding by memory ID from Qdrant", error=str(e)
            )
            return None

    def delete_embedding(self, point_id: str) -> bool:
        """Delete an embedding by point ID"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.PointIdsList(points=[point_id]),
            )
            self.observability.record_memory_operation("qdrant_delete", "success", "tier2")
            return True

        except Exception as e:
            self.observability.record_memory_operation("qdrant_delete", "failed", "tier2")
            self.observability.log_structured(
                "error", "Error deleting embedding from Qdrant", error=str(e)
            )
            return False

    def delete_embedding_by_memory_id(self, memory_id: int) -> bool:
        """Delete an embedding by PostgreSQL memory ID"""
        try:
            self.client.delete(
                collection_name=self.collection_name,
                points_selector=models.FilterSelector(
                    filter=models.Filter(
                        must=[
                            models.FieldCondition(
                                key="memory_id",
                                match=models.MatchValue(value=memory_id),
                            )
                        ]
                    )
                ),
            )
            self.observability.record_memory_operation("qdrant_delete_by_memory_id", "success", "tier2")
            return True

        except Exception as e:
            self.observability.record_memory_operation("qdrant_delete_by_memory_id", "failed", "tier2")
            self.observability.log_structured(
                "error", "Error deleting embedding by memory ID from Qdrant", error=str(e)
            )
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
            self.observability.log_structured(
                "error", "Error getting collection info from Qdrant", error=str(e)
            )
            return None

    def generate_placeholder_embedding(self, text: str) -> List[float]:
        """
        Placeholder embedding function for development.
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
