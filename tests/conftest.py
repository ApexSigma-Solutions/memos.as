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
    Provide a fresh asyncio event loop for the test session.
    
    Yields an event loop for use in tests and closes it when the session ends.
    
    Returns:
        asyncio.AbstractEventLoop: The event loop instance supplied to tests.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock database fixtures
@pytest.fixture
def mock_db_session():
    """
    Provide a Mock object that simulates a synchronous database session for tests.
    
    Returns:
        Mock: A mock session with `commit`, `rollback`, `close`, and `query` attributes preconfigured as Mock objects.
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
    Provide an AsyncMock representing an asynchronous database session for tests.
    
    The returned mock exposes awaitable methods commonly used by async DB sessions: `commit`, `rollback`, `close`, and `execute`, each implemented as an `AsyncMock`.
    
    Returns:
        AsyncMock: A mock async session with `commit`, `rollback`, `close`, and `execute` methods.
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
    Create a Mock Redis-like client configured for common cache operations used in tests.
    
    Returns:
        Mock: A mock object exposing `get`, `set`, `delete`, and `exists` methods configured to return `None`, `True`, `True`, and `False` respectively.
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
    Create a mock RabbitMQ client exposing `publish`, `consume`, and `close` methods for tests.
    
    Returns:
        Mock: A Mock object with `publish` (returns `True`), `consume` (returns an empty list), and `close` callables.
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
    Provide a sample memo dictionary for use in tests.
    
    Returns:
        dict: A memo object with fields:
            - id (str): Unique memo identifier, e.g. "test-memo-123".
            - title (str): Memo title.
            - content (str): Memo body content.
            - created_at (str): ISO 8601 timestamp for creation.
            - updated_at (str): ISO 8601 timestamp for last update.
            - author (str): Author identifier.
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
    Provide a sample user dictionary for tests.
    
    Returns:
        dict: A sample user with keys:
            - "id" (str): unique identifier for the user.
            - "username" (str): display username.
            - "email" (str): contact email address.
            - "role" (str): user role (e.g., "user").
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
    Provide a dictionary of default test configuration settings.
    
    Returns:
        dict: Mapping with the following keys:
            - database_url: database connection URL for tests (e.g., in-memory SQLite).
            - redis_url: Redis connection URL used by tests.
            - rabbitmq_url: RabbitMQ connection URL used by tests.
            - log_level: logging level for tests (e.g., "DEBUG").
            - testing: boolean flag indicating test mode (`True`).
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
    Run a teardown step after each test to perform post-test cleanup.
    
    This autouse fixture yields control to the test and, after the test finishes, executes any cleanup logic. Currently no cleanup actions are performed.
    """
    yield
    # Add cleanup logic here if needed
    pass