# Memos.as Test Suite

Comprehensive testing infrastructure for the memos.as service following pytest-cov best practices.

## Test Structure

```
tests/
├── __init__.py                 # Test suite initialization
├── conftest.py                 # Shared fixtures and configuration
├── README.md                   # This file
├── unit/                       # Unit tests
│   ├── __init__.py
│   ├── conftest.py            # Unit test specific fixtures
│   └── test_*.py              # Unit test files
├── integration/                # Integration tests
│   ├── __init__.py
│   ├── conftest.py            # Integration test specific fixtures
│   └── test_*.py              # Integration test files
└── e2e/                        # End-to-end tests
    ├── __init__.py
    ├── conftest.py            # E2E test specific fixtures
    └── test_*.py              # E2E test files
```

## Test Categories

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual functions, methods, and classes in isolation
- **Dependencies**: Mocked external services and dependencies
- **Speed**: Fast (< 1 second per test)
- **Markers**: `@pytest.mark.unit`
- **Coverage Target**: 90%+

**What to test**:
- Business logic functions
- Data validation
- Utility functions
- Model methods
- Schema validation

**Example**:
```python
@pytest.mark.unit
def test_memo_validation(sample_memo_data):
    memo = Memo(**sample_memo_data)
    assert memo.title == "Test Memo"
    assert memo.is_valid()
```

### Integration Tests (`tests/integration/`)
- **Purpose**: Test interactions between multiple components
- **Dependencies**: Real or test instances of databases, caches, message queues
- **Speed**: Medium (1-10 seconds per test)
- **Markers**: `@pytest.mark.integration`
- **Coverage Target**: 80%+

**What to test**:
- Database operations
- API endpoints
- Service-to-service communication
- Cache operations
- Message queue operations

**Example**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_memo_crud_operations(integration_db_connection):
    # Create
    memo = await create_memo(integration_db_connection, sample_data)
    assert memo.id is not None
    
    # Read
    retrieved = await get_memo(integration_db_connection, memo.id)
    assert retrieved.title == sample_data["title"]
    
    # Update
    updated = await update_memo(integration_db_connection, memo.id, {"title": "Updated"})
    assert updated.title == "Updated"
    
    # Delete
    result = await delete_memo(integration_db_connection, memo.id)
    assert result is True
```

### End-to-End Tests (`tests/e2e/`)
- **Purpose**: Test complete user workflows and system behavior
- **Dependencies**: Full service stack running
- **Speed**: Slow (10+ seconds per test)
- **Markers**: `@pytest.mark.e2e`
- **Coverage Target**: Critical paths only

**What to test**:
- Complete user workflows
- Authentication and authorization flows
- Cross-service interactions
- External API integrations
- Performance and load scenarios

**Example**:
```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_complete_memo_workflow(e2e_http_client, e2e_auth_token):
    headers = {"Authorization": f"Bearer {e2e_auth_token}"}
    
    # Create memo
    response = await e2e_http_client.post(
        "/api/memos",
        json={"title": "E2E Test", "content": "Test content"},
        headers=headers
    )
    assert response.status_code == 201
    memo_id = response.json()["id"]
    
    # Retrieve memo
    response = await e2e_http_client.get(f"/api/memos/{memo_id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["title"] == "E2E Test"
    
    # Delete memo
    response = await e2e_http_client.delete(f"/api/memos/{memo_id}", headers=headers)
    assert response.status_code == 204
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Categories
```bash
# Unit tests only
pytest tests/unit/ -m unit

# Integration tests only
pytest tests/integration/ -m integration

# E2E tests only
pytest tests/e2e/ -m e2e
```

### Run with Coverage
```bash
# All tests with coverage
pytest --cov=app --cov-report=html

# Specific category with coverage
pytest tests/unit/ --cov=app --cov-report=term-missing
```

### Run Slow Tests
```bash
# Exclude slow tests
pytest -m "not slow"

# Run only slow tests
pytest -m slow
```

### Run Async Tests
```bash
# Run only async tests
pytest -m asyncio
```

## Coverage Goals

- **Overall Coverage**: 80%+
- **Unit Test Coverage**: 90%+
- **Integration Test Coverage**: 80%+
- **Critical Paths**: 100%

## Writing Tests

### Test File Naming
- Unit tests: `test_<module_name>.py`
- Integration tests: `test_<feature>_integration.py`
- E2E tests: `test_<workflow>_e2e.py`

### Test Function Naming
```python
def test_<function>_<scenario>_<expected_result>():
    """Clear description of what is being tested."""
    # Arrange
    # Act
    # Assert
```

### Using Fixtures
```python
def test_with_fixtures(mock_db_session, sample_memo_data, mock_logger):
    """Test that uses multiple fixtures."""
    # Use fixtures in your test
    result = create_memo(mock_db_session, sample_memo_data, mock_logger)
    assert result is not None
```

### Markers
```python
import pytest

@pytest.mark.unit
def test_unit_example():
    pass

@pytest.mark.integration
@pytest.mark.slow
async def test_integration_example():
    pass

@pytest.mark.e2e
@pytest.mark.asyncio
async def test_e2e_example():
    pass
```

## Test Data Management

### Fixtures for Test Data
- Use fixtures defined in `conftest.py` for common test data
- Create specific fixtures in test files for unique scenarios
- Use factories for creating multiple test objects

### Test Database
- Integration and E2E tests should use a separate test database
- Database should be cleaned before/after each test
- Use transactions when possible for faster cleanup

## Continuous Integration

Tests run automatically on:
- Every commit (unit tests)
- Pull requests (unit + integration tests)
- Main branch merges (all tests including e2e)
- Scheduled runs (nightly full test suite)

## Best Practices

1. **Isolation**: Each test should be independent
2. **Clarity**: Test names should clearly describe what is being tested
3. **Simplicity**: One assertion per test when possible
4. **Speed**: Keep tests fast, especially unit tests
5. **Maintenance**: Update tests when code changes
6. **Documentation**: Comment complex test scenarios
7. **Cleanup**: Always clean up resources after tests
8. **Mocking**: Mock external dependencies in unit tests
9. **Coverage**: Aim for high coverage but focus on quality over quantity
10. **Async**: Use proper async/await patterns for async code

## Troubleshooting

### Tests Hanging
- Check for unclosed connections or resources
- Verify async/await usage
- Check for infinite loops or timeouts

### Import Errors
- Ensure `PYTHONPATH` includes the project root
- Check `pytest.ini` configuration
- Verify all `__init__.py` files exist

### Coverage Not Recording
- Ensure source paths are correct in `pytest.ini`
- Check that tests are actually running
- Verify coverage configuration in `pyproject.toml`

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [ApexSigma Testing Guidelines](../../docs/testing-guidelines.md)
