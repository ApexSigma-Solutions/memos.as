"""
Mock services and utilities for testing.

This module provides mock implementations of external services
and utilities to facilitate testing.
"""

from typing import Any, Dict, List, Optional
from unittest.mock import Mock, AsyncMock


class MockDatabase:
    """Mock database for testing."""
    
    def __init__(self):
        self.data: Dict[str, Any] = {}
        self.call_count = 0
    
    def insert(self, table: str, data: Dict[str, Any]) -> str:
        """Mock insert operation."""
        self.call_count += 1
        item_id = f"{table}_{len(self.data)}"
        self.data[item_id] = {"table": table, **data}
        return item_id
    
    def get(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Mock get operation."""
        self.call_count += 1
        return self.data.get(item_id)
    
    def update(self, item_id: str, data: Dict[str, Any]) -> bool:
        """Mock update operation."""
        self.call_count += 1
        if item_id in self.data:
            self.data[item_id].update(data)
            return True
        return False
    
    def delete(self, item_id: str) -> bool:
        """Mock delete operation."""
        self.call_count += 1
        if item_id in self.data:
            del self.data[item_id]
            return True
        return False
    
    def clear(self):
        """Clear all data."""
        self.data.clear()
        self.call_count = 0


class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self.cache: Dict[str, str] = {}
        self.ttl: Dict[str, int] = {}
    
    def get(self, key: str) -> Optional[str]:
        """Mock get operation."""
        return self.cache.get(key)
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """Mock set operation."""
        self.cache[key] = value
        if ex:
            self.ttl[key] = ex
        return True
    
    def delete(self, key: str) -> int:
        """Mock delete operation."""
        if key in self.cache:
            del self.cache[key]
            if key in self.ttl:
                del self.ttl[key]
            return 1
        return 0
    
    def exists(self, key: str) -> int:
        """Mock exists operation."""
        return 1 if key in self.cache else 0
    
    def clear(self):
        """Clear all cache data."""
        self.cache.clear()
        self.ttl.clear()


class MockMessageQueue:
    """Mock message queue for testing."""
    
    def __init__(self):
        self.messages: List[Dict[str, Any]] = []
        self.published_count = 0
        self.consumed_count = 0
    
    def publish(self, queue: str, message: Dict[str, Any]) -> bool:
        """Mock publish operation."""
        self.messages.append({"queue": queue, "message": message})
        self.published_count += 1
        return True
    
    def consume(self, queue: str, count: int = 1) -> List[Dict[str, Any]]:
        """Mock consume operation."""
        result = []
        for msg in self.messages:
            if msg["queue"] == queue and len(result) < count:
                result.append(msg["message"])
                self.consumed_count += 1
        return result
    
    def clear(self):
        """Clear all messages."""
        self.messages.clear()
        self.published_count = 0
        self.consumed_count = 0


class MockHTTPClient:
    """Mock HTTP client for testing."""
    
    def __init__(self):
        self.requests: List[Dict[str, Any]] = []
        self.responses: Dict[str, Any] = {}
    
    async def get(self, url: str, **kwargs) -> Mock:
        """Mock GET request."""
        self.requests.append({"method": "GET", "url": url, **kwargs})
        response = Mock()
        response.status_code = self.responses.get(url, {}).get("status_code", 200)
        response.json = Mock(return_value=self.responses.get(url, {}).get("json", {}))
        return response
    
    async def post(self, url: str, **kwargs) -> Mock:
        """Mock POST request."""
        self.requests.append({"method": "POST", "url": url, **kwargs})
        response = Mock()
        response.status_code = self.responses.get(url, {}).get("status_code", 201)
        response.json = Mock(return_value=self.responses.get(url, {}).get("json", {}))
        return response
    
    async def put(self, url: str, **kwargs) -> Mock:
        """Mock PUT request."""
        self.requests.append({"method": "PUT", "url": url, **kwargs})
        response = Mock()
        response.status_code = self.responses.get(url, {}).get("status_code", 200)
        response.json = Mock(return_value=self.responses.get(url, {}).get("json", {}))
        return response
    
    async def delete(self, url: str, **kwargs) -> Mock:
        """Mock DELETE request."""
        self.requests.append({"method": "DELETE", "url": url, **kwargs})
        response = Mock()
        response.status_code = self.responses.get(url, {}).get("status_code", 204)
        response.json = Mock(return_value=self.responses.get(url, {}).get("json", {}))
        return response
    
    def set_response(self, url: str, status_code: int, json_data: Dict[str, Any]):
        """Set mock response for a URL."""
        self.responses[url] = {"status_code": status_code, "json": json_data}
    
    def clear(self):
        """Clear all requests and responses."""
        self.requests.clear()
        self.responses.clear()
