"""
Unit test specific fixtures and configuration.

This module provides fixtures specifically for unit tests that focus on
testing individual functions, methods, and classes in isolation.
"""

import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def mock_logger():
    """Mock logger for unit tests."""
    logger = Mock()
    logger.info = Mock()
    logger.debug = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.exception = Mock()
    return logger


@pytest.fixture
def mock_http_client():
    """Mock HTTP client for unit tests."""
    client = Mock()
    client.get = Mock()
    client.post = Mock()
    client.put = Mock()
    client.delete = Mock()
    return client


@pytest.fixture
def isolated_environment(monkeypatch):
    """Set up an isolated environment for unit tests."""
    # Set test environment variables
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    return monkeypatch
