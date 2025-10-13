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
        Initialize the mock database with empty storage and reset the operation counter.
        
        Creates:
            data (Dict[str, Any]): In-memory mapping of item IDs to their stored data.
            call_count (int): Total number of operations performed, initialized to 0.
        """
        self.data: Dict[str, Any] = {}
        self.call_count = 0
    
    def insert(self, table: str, data: Dict[str, Any]) -> str:
        """
        Insert the provided record into the mock database and record the operation.
        
        Stores the given data under a generated item id and increments the internal call_count.
        
        Parameters:
            table (str): Name of the table/namespace for the record.
            data (Dict[str, Any]): Field values to store for the new record.
        
        Returns:
            item_id (str): The generated id for the new record (format: '{table}_{index}').
        """
        self.call_count += 1
        item_id = f"{table}_{len(self.data)}"
        self.data[item_id] = {"table": table, **data}
        return item_id
    
    def get(self, item_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve the stored item for the given item ID. Increments the mock's call_count.
        
        Returns:
            The stored item as a dict if present, otherwise `None`.
        """
        self.call_count += 1
        return self.data.get(item_id)
    
    def update(self, item_id: str, data: Dict[str, Any]) -> bool:
        """
        Update an existing stored item by merging the provided fields into its data.
        
        Increments the instance's call_count.
        
        Parameters:
            item_id (str): Identifier of the item to update.
            data (Dict[str, Any]): Fields to merge into the existing item; existing keys will be overwritten.
        
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
        Remove an item from the mock database by its identifier.
        
        Returns:
            True if the item existed and was removed, False otherwise.
        """
        self.call_count += 1
        if item_id in self.data:
            del self.data[item_id]
            return True
        return False
    
    def clear(self):
        """
        Clear all stored items and reset the operation counter.
        
        Empties the in-memory data store and sets `call_count` to 0.
        """
        self.data.clear()
        self.call_count = 0


class MockRedis:
    """Mock Redis client for testing."""
    
    def __init__(self):
        """
        Initialize an in-memory key-value cache and TTL store for the mock Redis client.
        
        Creates two empty dictionaries used to record state during tests.
        
        Attributes:
            cache (Dict[str, str]): Mapping of keys to string values.
            ttl (Dict[str, int]): Mapping of keys to their TTL (time-to-live) in seconds.
        """
        self.cache: Dict[str, str] = {}
        self.ttl: Dict[str, int] = {}
    
    def get(self, key: str) -> Optional[str]:
        """
        Retrieve the value associated with `key` from the mock cache.
        
        Returns:
            value (Optional[str]): The string value stored for `key`, or `None` if the key is not present.
        """
        return self.cache.get(key)
    
    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        """
        Store a string value under a key with an optional time-to-live (TTL).
        
        Parameters:
            key (str): The cache key.
            value (str): The string value to store.
            ex (Optional[int]): Expiration time for the key in seconds; if provided, the TTL is recorded.
        
        Returns:
            bool: `True` if the value was stored, `False` otherwise.
        """
        self.cache[key] = value
        if ex:
            self.ttl[key] = ex
        return True
    
    def delete(self, key: str) -> int:
        """
        Remove a key from the mock Redis cache and its associated TTL if present.
        
        If the key exists, it is removed from the cache and any stored TTL is cleared.
        
        Returns:
            int: `1` if the key was present and removed, `0` otherwise.
        """
        if key in self.cache:
            del self.cache[key]
            if key in self.ttl:
                del self.ttl[key]
            return 1
        return 0
    
    def exists(self, key: str) -> int:
        """
        Check whether a key exists in the mock Redis cache.
        
        Returns:
            int: `1` if the key exists, `0` otherwise.
        """
        return 1 if key in self.cache else 0
    
    def clear(self):
        """
        Clear all stored keys and their expiration entries from the mock Redis client.
        
        Removes every entry from the internal cache and the TTL mapping, restoring an empty state.
        """
        self.cache.clear()
        self.ttl.clear()


class MockMessageQueue:
    """Mock message queue for testing."""
    
    def __init__(self):
        """
        Create a new MockMessageQueue and initialize its internal state.
        
        Attributes:
            messages (List[Dict[str, Any]]): Stored messages; each entry contains at least 'queue' and 'message' keys.
            published_count (int): Total number of messages published to the queue.
            consumed_count (int): Total number of messages consumed from the queue.
        """
        self.messages: List[Dict[str, Any]] = []
        self.published_count = 0
        self.consumed_count = 0
    
    def publish(self, queue: str, message: Dict[str, Any]) -> bool:
        """
        Publish a message to the mock queue.
        
        Records the provided message under the given queue and increments the published message counter.
        
        Parameters:
            queue (str): Name of the target queue.
            message (Dict[str, Any]): Payload to publish to the queue.
        
        Returns:
            bool: `True` if the message was recorded, `False` otherwise.
        """
        self.messages.append({"queue": queue, "message": message})
        self.published_count += 1
        return True
    
    def consume(self, queue: str, count: int = 1) -> List[Dict[str, Any]]:
        """
        Retrieve up to `count` messages for the specified queue.
        
        This returns a list of message payloads from the in-memory store for `queue`, up to `count` items. For each message returned `self.consumed_count` is incremented. Returned messages remain in the internal message list (they are not removed).
        
        Parameters:
            queue (str): Name of the queue to consume from.
            count (int): Maximum number of messages to retrieve.
        
        Returns:
            List[Dict[str, Any]]: Message payloads retrieved from the queue, in the order they were stored, up to `count` items.
        """
        result = []
        for msg in self.messages:
            if msg["queue"] == queue and len(result) < count:
                result.append(msg["message"])
                self.consumed_count += 1
        return result
    
    def clear(self):
        """
        Clear all stored messages and reset publish/consume counters.
        
        Removes all messages from the queue and sets `published_count` and `consumed_count` to 0.
        """
        self.messages.clear()
        self.published_count = 0
        self.consumed_count = 0


class MockHTTPClient:
    """Mock HTTP client for testing."""
    
    def __init__(self):
        """
        Initialize the mock HTTP client by setting up storage for recorded requests and configured responses.
        
        Attributes:
            requests: List of recorded request metadata dictionaries (each contains at least `method`, `url`, and `kwargs`).
            responses: Mapping from URL to a response configuration dictionary (commonly contains `status_code` and `json` payload) used to construct mock responses.
        """
        self.requests: List[Dict[str, Any]] = []
        self.responses: Dict[str, Any] = {}
    
    async def get(self, url: str, **kwargs) -> Mock:
        """
        Builds and returns a configured mock response for an HTTP GET and records the request.
        
        Records the request as {"method": "GET", "url": url, **kwargs} appended to self.requests. The returned Mock has a numeric `status_code` taken from this client's configured responses for the URL (defaults to 200) and a `json()` callable that returns the configured JSON payload for the URL (defaults to an empty dict).
        
        Parameters:
            url (str): The request URL.
            **kwargs: Additional request metadata that will be recorded with the request.
        
        Returns:
            Mock: A mock response where `status_code` is the HTTP status and `json()` returns the response payload.
        """
        self.requests.append({"method": "GET", "url": url, **kwargs})
        response = Mock()
        response.status_code = self.responses.get(url, {}).get("status_code", 200)
        response.json = Mock(return_value=self.responses.get(url, {}).get("json", {}))
        return response
    
    async def post(self, url: str, **kwargs) -> Mock:
        """
        Create a mocked POST HTTP response and record the request.
        
        The function appends the request metadata (method, url and provided kwargs) to the client's request log and returns a Mock response object. The response's `status_code` is taken from the client's configured responses for `url` (defaults to 201) and its `json()` method returns the configured JSON payload for `url` (defaults to an empty dict).
        
        @returns:
            Mock: A Mock object representing the HTTP response with `status_code` and a callable `json()` returning the payload.
        """
        self.requests.append({"method": "POST", "url": url, **kwargs})
        response = Mock()
        response.status_code = self.responses.get(url, {}).get("status_code", 201)
        response.json = Mock(return_value=self.responses.get(url, {}).get("json", {}))
        return response
    
    async def put(self, url: str, **kwargs) -> Mock:
        """
        Builds and returns a Mock HTTP PUT response and records the request.
        
        Records the PUT request (method, url and provided kwargs) in self.requests. The returned Mock has a `status_code` attribute taken from the configured responses for the URL (default 200) and a `json()` callable that returns the configured JSON payload for the URL (default {}).
        
        Returns:
            Mock: Mock response object with `status_code` and `json()` behavior as described.
        """
        self.requests.append({"method": "PUT", "url": url, **kwargs})
        response = Mock()
        response.status_code = self.responses.get(url, {}).get("status_code", 200)
        response.json = Mock(return_value=self.responses.get(url, {}).get("json", {}))
        return response
    
    async def delete(self, url: str, **kwargs) -> Mock:
        """
        Builds and returns a mocked HTTP DELETE response and records the request.
        
        Parameters:
            url (str): The request URL.
            **kwargs: Additional request metadata recorded for inspection (e.g., headers, params).
        
        Returns:
            Mock: A response-like Mock whose `status_code` is taken from the configured responses for `url` (default 204) and whose `json()` method returns the configured JSON payload for `url` (default {}).
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
            url (str): The request URL to associate the response with.
            status_code (int): The HTTP status code to return for requests to `url`.
            json_data (Dict[str, Any]): The JSON-serializable payload to return as the response body.
        """
        self.responses[url] = {"status_code": status_code, "json": json_data}
    
    def clear(self):
        """Clear all requests and responses."""
        self.requests.clear()
        self.responses.clear()