"""
Unit test specific fixtures and configuration.

This module provides fixtures specifically for unit tests that focus on
testing individual functions, methods, and classes in isolation.
"""

import pytest
from unittest.mock import Mock, patch


@pytest.fixture
def mock_logger():
    """
    Create a Mock-based logger exposing common logging methods for unit tests.
    
    Returns:
        Mock: A Mock object with `info`, `debug`, `warning`, `error`, and `exception` attributes, each a Mock.
    """
    logger = Mock()
    logger.info = Mock()
    logger.debug = Mock()
    logger.warning = Mock()
    logger.error = Mock()
    logger.exception = Mock()
    return logger


@pytest.fixture
def mock_http_client():
    """
    Create a Mock HTTP client with common HTTP verb methods for unit tests.
    
    The returned object has `get`, `post`, `put`, and `delete` attributes, each set to a `Mock` so tests can assert calls and configure return values.
    
    Returns:
        client (Mock): Mock object representing an HTTP client with mocked verb methods.
    """
    client = Mock()
    client.get = Mock()
    client.post = Mock()
    client.put = Mock()
    client.delete = Mock()
    return client


@pytest.fixture
def isolated_environment(monkeypatch):
    """
    Configure environment variables for unit tests.
    
    Sets ENVIRONMENT to "test" and LOG_LEVEL to "DEBUG" on the provided pytest monkeypatch fixture.
    
    Returns:
        monkeypatch: The same monkeypatch object passed in, with the environment variables applied.
    """
    # Set test environment variables
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    return monkeypatch