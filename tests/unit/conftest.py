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
    Create a Mock-based logger for unit tests.
    
    Returns:
        logger (unittest.mock.Mock): A Mock configured with callable attributes `info`, `debug`, `warning`, `error`, and `exception` (each a Mock) to capture and assert logging calls.
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
    Provide a mock HTTP client exposing common request methods for unit tests.
    
    Each of the client's `get`, `post`, `put`, and `delete` attributes is a Mock that can be configured and asserted against in tests.
    
    Returns:
        client (Mock): Mock object representing an HTTP client with `get`, `post`, `put`, and `delete` mocks.
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
    Configure a pytest monkeypatch to provide an isolated environment for unit tests.
    
    Sets environment variables ENVIRONMENT to "test" and LOG_LEVEL to "DEBUG", and returns the provided monkeypatch object so callers can further modify or inspect it.
    
    Parameters:
        monkeypatch: pytest.MonkeyPatch
            The pytest monkeypatch fixture to configure.
    
    Returns:
        pytest.MonkeyPatch: The same monkeypatch instance after applying the environment changes.
    """
    # Set test environment variables
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    return monkeypatch