"""
Shared test fixtures and configuration for memos.as test suite.

This module provides common fixtures, mocks, and test utilities used across
unit, integration, and e2e tests.
"""

import pytest
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import Mock, AsyncMock


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "unit: Unit tests")
    config.addinivalue_line("markers", "integration: Integration tests")
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "slow: Slow running tests")
    config.addinivalue_line("markers", "asyncio: Async tests")


# Event loop fixture for async tests
@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """
    Create and provide a fresh asyncio event loop for the test session, closing it after the session ends.
    
    Returns:
        loop (asyncio.AbstractEventLoop): A newly created event loop for the test session.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock database fixtures
@pytest.fixture
def mock_db_session():
    """
    Provide a synchronous Mock that simulates a database session for tests.
    
    The returned Mock exposes `commit`, `rollback`, `close`, and `query` attributes, each set to a Mock so call sites can be asserted against.
    
    Returns:
        session (Mock): Mock object representing a DB session with mocked `commit`, `rollback`, `close`, and `query` methods.
    """
    session = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.query = Mock()
    return session


@pytest.fixture
async def async_mock_db_session():
    """
    Create an AsyncMock that simulates an asynchronous database session for tests.
    
    The returned mock includes async methods `commit`, `rollback`, `close`, and `execute` to mirror common session operations.
    
    Returns:
        session (AsyncMock): An AsyncMock instance representing an async DB session with async `commit`, `rollback`, `close`, and `execute` methods.
    """
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    return session


# Mock external service fixtures
@pytest.fixture
def mock_redis_client():
    """
    Create a Mock object that simulates a Redis client with common cache methods.
    
    The returned mock provides `get`, `set`, `delete`, and `exists` callables with deterministic default return values:
    - `get` returns `None`
    - `set` returns `True`
    - `delete` returns `True`
    - `exists` returns `False`
    
    Returns:
        Mock: A Mock configured to act like a Redis client for tests.
    """
    client = Mock()
    client.get = Mock(return_value=None)
    client.set = Mock(return_value=True)
    client.delete = Mock(return_value=True)
    client.exists = Mock(return_value=False)
    return client


@pytest.fixture
def mock_rabbitmq_client():
    """
    Provides a mock RabbitMQ client with common message-queue operations for tests.
    
    The returned mock exposes:
    - publish(...): returns True
    - consume(...): returns an empty list
    - close(): callable mock for closing the client
    
    Returns:
        Mock: A Mock object simulating a RabbitMQ client with the methods above.
    """
    client = Mock()
    client.publish = Mock(return_value=True)
    client.consume = Mock(return_value=[])
    client.close = Mock()
    return client


# Test data factories
@pytest.fixture
def sample_memo_data():
    """
    Provide a sample memo dictionary used in tests.
    
    Returns:
        dict: A memo object with keys:
            - id (str): Memo identifier.
            - title (str): Memo title.
            - content (str): Memo body text.
            - created_at (str): ISO 8601 creation timestamp.
            - updated_at (str): ISO 8601 last-updated timestamp.
            - author (str): Author username or identifier.
            - tags (list[str]): List of tag strings associated with the memo.
    """
    return {
        "id": "test-memo-123",
        "title": "Test Memo",
        "content": "This is a test memo content",
        "created_at": "2025-10-08T00:00:00Z",
        "updated_at": "2025-10-08T00:00:00Z",
        "author": "test-user",
        "tags": ["test", "sample"]
    }


@pytest.fixture
def sample_user_data():
    """
    Sample user fixture data for tests.
    
    Returns:
        dict: User data with keys:
            - `id` (str): Unique identifier for the user.
            - `username` (str): User's login name.
            - `email` (str): User's email address.
            - `role` (str): User role (e.g., "user", "admin").
    """
    return {
        "id": "test-user-123",
        "username": "testuser",
        "email": "test@example.com",
        "role": "user"
    }


# Configuration fixtures
@pytest.fixture
def test_config():
    """
    Provide a default test configuration dictionary for use by the test suite.
    
    Returns:
        dict: Configuration containing:
            - database_url (str): Database connection URL for tests.
            - redis_url (str): Redis connection URL for tests.
            - rabbitmq_url (str): RabbitMQ connection URL for tests.
            - log_level (str): Logging level to use during tests.
            - testing (bool): Flag indicating the environment is for testing.
    """
    return {
        "database_url": "sqlite:///:memory:",
        "redis_url": "redis://localhost:6379/0",
        "rabbitmq_url": "amqp://guest:guest@localhost:5672/",
        "log_level": "DEBUG",
        "testing": True
    }


# Cleanup fixture
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """
    Run teardown logic after each test.
    
    This autouse fixture yields to the test and then performs any necessary post-test cleanup. It is a placeholder for project-specific teardown steps and currently performs no actions.
    """
    yield
    # Add cleanup logic here if needed
    pass