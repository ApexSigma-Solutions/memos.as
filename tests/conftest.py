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
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Mock database fixtures
@pytest.fixture
def mock_db_session():
    """Mock database session for unit tests."""
    session = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.query = Mock()
    return session


@pytest.fixture
async def async_mock_db_session():
    """Mock async database session for async unit tests."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    return session


# Mock external service fixtures
@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing cache operations."""
    client = Mock()
    client.get = Mock(return_value=None)
    client.set = Mock(return_value=True)
    client.delete = Mock(return_value=True)
    client.exists = Mock(return_value=False)
    return client


@pytest.fixture
def mock_rabbitmq_client():
    """Mock RabbitMQ client for testing message queue operations."""
    client = Mock()
    client.publish = Mock(return_value=True)
    client.consume = Mock(return_value=[])
    client.close = Mock()
    return client


# Test data factories
@pytest.fixture
def sample_memo_data():
    """Sample memo data for testing."""
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
    """Sample user data for testing."""
    return {
        "id": "test-user-123",
        "username": "testuser",
        "email": "test@example.com",
        "role": "user"
    }


# Configuration fixtures
@pytest.fixture
def test_config():
    """Test configuration settings."""
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
    """Cleanup after each test."""
    yield
    # Add cleanup logic here if needed
    pass
