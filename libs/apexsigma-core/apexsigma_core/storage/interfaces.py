from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class CacheStorage(ABC):
    @abstractmethod
    def get(self, key: str) -> Any:
        pass

    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        pass

    @abstractmethod
    def delete(self, key: str) -> None:
        pass


class PersistentStorage(ABC):
    @abstractmethod
    def get(self, id: str) -> Dict:
        pass

    @abstractmethod
    def save(self, data: Dict) -> str:
        pass

    @abstractmethod
    def update(self, id: str, data: Dict) -> None:
        pass

    @abstractmethod
    def delete(self, id: str) -> None:
        pass


class VectorStorage(ABC):
    @abstractmethod
    def search(self, query_vector: List[float], top_k: int) -> List[Dict]:
        pass

    @abstractmethod
    def upsert(self, vectors: List[Dict]) -> None:
        pass


class GraphStorage(ABC):
    @abstractmethod
    def execute_query(self, query: str, params: Optional[Dict] = None) -> Any:
        pass
