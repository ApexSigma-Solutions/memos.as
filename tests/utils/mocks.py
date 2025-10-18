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
        """
        Initialize the mock database instance with empty storage and reset counters.
        
        Attributes:
            data (Dict[str, Any]): In-memory mapping of item IDs to stored records.
            call_count (int): Number of database operations invoked, initialized to 0.
        """
        self.data: Dict[str, Any] = {}
        self.call_count = 0
    
    def insert(self, table: str, data: Dict[str, Any]) -> str:
        """
        Create and store a new item in the mock database and return its generated identifier.
        
        Parameters:
            table (str): Name of the table/namespace used to construct the item id.
            data (Dict[str, Any]): Item fields to store.
        
        Returns:
            item_id (str): Generated identifier in the form "<table>_<n>", where n is the number of items present before insertion.
        """
        self.call_count += 1
        item_id = f"{table}_{len(self.data)}"
        self.data[item_id] = {"table": table, **data}
        return item_id
    
    def get(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an item from the mock database by its identifier.
        
        Also increments the mock's internal operation counter.
        
        Returns:
            Dict[str, Any]: The stored item for `item_id` if present, `None` otherwise.
        """
        self.call_count += 1
        return self.data.get(item_id)
    
    def update(self, item_id: str, data: Dict[str, Any]) -> bool:
        """
        Update fields of an existing stored item.
        
        This mutates the stored item by merging the provided mapping into its data and increments the instance's operation counter.
        
        Parameters:
            item_id (str): Identifier of the item to update.
            data (Dict[str, Any]): Mapping of fields and values to merge into the stored item.
        
        Returns:
            bool: `True` if the item existed and was updated, `False` otherwise.
        """
        self.call_count += 1
        if item_id in self.data:
            self.data[item_id].update(data)
            return True
        return False
    
    def delete(self, item_id: str) -> bool:
        """
        Remove the item with the given item_id from the mock database.
        
        Parameters:
            item_id (str): Identifier of the item to remove.
        
        Returns:
            bool: True if the item existed and was removed, False otherwise.
        """
        self.call_count += 1
        if item_id in self.data:
            del self.data[item_id]
            return True
        return False
    
    def clear(self):
        """
        Clear all stored items and reset the call counter.
        
        Empties the internal in-memory data store and sets `call_count` to 0.
        """
        self.data.clear()
        self.call_count = 0


class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        """
        Initialize the mock Redis client with empty in-memory storage.
        
        Creates:
        - `cache`: a mapping from keys to string values.
        - `ttl`: a mapping from keys to their time-to-live (in seconds).
        """
        self.cache: Dict[str, str] = {}
        self.ttl: Dict[str, int] = {}
    
    def get(self, key: str) -> Optional[str]:
        """
        Retrieve the string value stored for a cache key.
        
        Returns:
            `str` value stored under `key`, or `None` if the key is not present.
        """
        return self.cache.get(key)
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Set a string value for a key in the mock cache and optionally record a time-to-live.
        
        Parameters:
            key (str): Cache key.
            value (str): Value to store.
            ex (Optional[int]): Time-to-live in seconds; if provided, the TTL is recorded for the key.
        
        Returns:
            bool: `True` if the value was stored.
        """
        self.cache[key] = value
        if ex:
            self.ttl[key] = ex
        return True
    
    def delete(self, key: str) -> int:
        """
        Remove a key from the mock Redis cache.
        
        If present, also removes any associated TTL entry.
        
        Parameters:
            key (str): The cache key to remove.
        
        Returns:
            int: `1` if the key was deleted, `0` if the key was not found.
        """
        if key in self.cache:
            del self.cache[key]
            if key in self.ttl:
                del self.ttl[key]
            return 1
        return 0
    
    def exists(self, key: str) -> int:
        """
        Check whether a key exists in the mock cache.
        
        Returns:
            int: `1` if the key exists, `0` otherwise.
        """
        return 1 if key in self.cache else 0
    
    def clear(self):
        """
        Clear all stored keys and their associated TTL entries.
        
        Removes all entries from the in-memory cache and the TTL mapping used to track expirations.
        """
        self.cache.clear()
        self.ttl.clear()


class MockMessageQueue:
    """Mock message queue for testing."""
    
    def __init__(self):
        """
        Initialize the in-memory message queue's state.
        
        Creates an empty `messages` list for enqueued message records (each containing `queue` and `payload`), and sets `published_count` and `consumed_count` counters to 0.
        """
        self.messages: List[Dict[str, Any]] = []
        self.published_count = 0
        self.consumed_count = 0
    
    def publish(self, queue: str, message: Dict[str, Any]) -> bool:
        """
        Enqueues a message into the mock message queue.
        
        Parameters:
            queue (str): Name of the target queue.
            message (Dict[str, Any]): Message payload to record.
        
        Returns:
            bool: `True` if the message was recorded.
        """
        self.messages.append({"queue": queue, "message": message})
        self.published_count += 1
        return True
    
    def consume(self, queue: str, count: int = 1) -> List[Dict[str, Any]]:
        """
        Consume up to `count` messages from the specified queue.
        
        Consumed messages are removed from the internal message store and increment the instance's `consumed_count`.
        
        Parameters:
        	queue (str): Name of the queue to consume messages from.
        	count (int): Maximum number of messages to consume.
        
        Returns:
        	List[Dict[str, Any]]: A list of message payloads that were consumed (in arrival order).
        """
        result = []
        to_remove = []
        for idx, msg in enumerate(self.messages):
            if msg["queue"] == queue and len(result) < count:
                result.append(msg["message"])
                to_remove.append(idx)
                self.consumed_count += 1
        # Remove consumed messages from self.messages
        for idx in reversed(to_remove):
            del self.messages[idx]
        return result
    
    def clear(self):
        """
        Remove all queued messages and reset the published and consumed counters.
        
        This empties the internal message store and sets both `published_count` and
        `consumed_count` to 0.
        """
        self.messages.clear()
        self.published_count = 0
        self.consumed_count = 0


class MockHTTPClient:
    """Mock HTTP client for testing."""
    
    def __init__(self):
        """
        Initialize the mock HTTP client, preparing storage for recorded requests and configurable responses.
        
        self.requests will hold recorded request descriptors (dicts with keys like method, url, and kwargs).
        self.responses will map URLs to configured mock response data.
        """
        self.requests: List[Dict[str, Any]] = []
        self.responses: Dict[str, Any] = {}
    
    async def get(self, url: str, **kwargs) -> Mock:
        """
        Create and return a mock GET response for the given URL and record the request.
        
        Parameters:
            url (str): The request URL. Additional keyword arguments are recorded alongside the request.
        
        Returns:
            Mock: A mock response whose `status_code` is the configured status for `url` (default 200) and whose `json()` returns the configured JSON payload for `url` (default {}).
        """
        self.requests.append({"method": "GET", "url": url, **kwargs})
        response = Mock()
        response.status_code = self.responses.get(url, {}).get("status_code", 200)
        response.json = Mock(return_value=self.responses.get(url, {}).get("json", {}))
        return response
    
    async def post(self, url: str, **kwargs) -> Mock:
        """
        Create a mock HTTP POST response and record the request.
        
        Records the POST request (method and URL plus kwargs) and returns a Mock response whose `status_code` and `json()` result are taken from the client's configured responses for the URL (defaults: status_code 201 and empty dict).
        
        Returns:
            Mock: A mock response object with `status_code` (int) and a callable `json()` that returns the configured JSON payload.
        """
        self.requests.append({"method": "POST", "url": url, **kwargs})
        response = Mock()
        response.status_code = self.responses.get(url, {}).get("status_code", 201)
        response.json = Mock(return_value=self.responses.get(url, {}).get("json", {}))
        return response
    
    async def put(self, url: str, **kwargs) -> Mock:
        """
        Create a mock HTTP PUT response and record the request in self.requests.
        
        The returned Mock has its `status_code` taken from configured responses for the URL (default 200)
        and its `json()` callable returning the configured JSON payload (default {}).
        
        Returns:
            Mock: mock response with `status_code` and a `json()` callable.
        """
        self.requests.append({"method": "PUT", "url": url, **kwargs})
        response = Mock()
        response.status_code = self.responses.get(url, {}).get("status_code", 200)
        response.json = Mock(return_value=self.responses.get(url, {}).get("json", {}))
        return response
    
    async def delete(self, url: str, **kwargs) -> Mock:
        """
        Create and record a mock HTTP DELETE request and return a configured response.
        
        The response's `status_code` and `json()` payload are taken from the client's configured responses for the URL, defaulting to 204 and an empty dict respectively.
        
        Returns:
            Mock: Mock response object with `status_code` and a `json()` method.
        """
        self.requests.append({"method": "DELETE", "url": url, **kwargs})
        response = Mock()
        response.status_code = self.responses.get(url, {}).get("status_code", 204)
        response.json = Mock(return_value=self.responses.get(url, {}).get("json", {}))
        return response
    
    def set_response(self, url: str, status_code: int, json_data: Dict[str, Any]):
        """
        Configure the mock HTTP response returned for a specific URL.
        
        Parameters:
            url (str): The request URL to mock.
            status_code (int): HTTP status code that the mock response should expose.
            json_data (Dict[str, Any]): JSON-serializable payload returned by the mock response's json().
        """
        self.responses[url] = {"status_code": status_code, "json": json_data}
    
    def clear(self):
        """Clear all requests and responses."""
        self.requests.clear()
        self.responses.clear()