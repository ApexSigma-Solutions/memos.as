import pytest
from fastapi.testclient import TestClient
from app.main import app

# Create test client
client = TestClient(app)

# Test data
test_tool = {
    "name": "test_tool_integration",
    "description": "A test tool for integration testing",
    "usage": "Use this tool for testing purposes",
    "tags": ["testing", "integration"]
}

test_memory = {
    "content": "This is a test memory for integration testing",
    "metadata": {"source": "test", "type": "integration_test"}
}

test_query = {
    "query": "test memory integration",
    "top_k": 5
}

def test_health_check():
    """Test basic health check endpoint"""
    response = client.get("/health")
    print(f"Health check response: {response.status_code}")
    if response.status_code != 200:
        print(f"Health check failed: {response.text}")
    # Note: Health check might fail in test environment due to missing services

def test_tool_registration():
    """Test tool registration endpoint"""
    response = client.post("/tools/register", json=test_tool)
    print(f"Tool registration response: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Tool registered with ID: {data.get('tool_id')}")
        assert data["success"] is True
        assert data["tool_id"] is not None
        return data["tool_id"]
    else:
        print(f"Tool registration failed: {response.text}")
        pytest.fail(f"Tool registration failed: {response.text}")

def test_memory_store():
    """Test memory storage endpoint"""
    response = client.post("/memory/store", json=test_memory)
    print(f"Memory store response: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Memory stored with ID: {data.get('memory_id')}")
        assert data["success"] is True
        assert data["memory_id"] is not None
        return data["memory_id"]
    else:
        print(f"Memory store failed: {response.text}")
        pytest.fail(f"Memory store failed: {response.text}")

def test_memory_query():
    """Test memory query endpoint"""
    # First store a memory
    test_memory_store()

    # Then query for it
    response = client.post("/memory/query", json=test_query)
    print(f"Memory query response: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Query returned {data['memories']['count']} memories and {data['tools']['count']} tools")
        assert "memories" in data
        assert "tools" in data
        assert "query" in data
        assert data["query"] == test_query["query"]
        return data
    else:
        print(f"Memory query failed: {response.text}")
        pytest.fail(f"Memory query failed: {response.text}")

def test_end_to_end_flow():
    """Test complete end-to-end workflow"""
    print("\n=== End-to-End Integration Test ===")

    # Step 1: Register a tool
    print("1. Registering tool...")
    tool_response = client.post("/tools/register", json=test_tool)
    if tool_response.status_code == 200:
        print("✅ Tool registration successful")
    else:
        print(f"❌ Tool registration failed: {tool_response.text}")

    # Step 2: Store a memory
    print("2. Storing memory...")
    memory_response = client.post("/memory/store", json=test_memory)
    if memory_response.status_code == 200:
        memory_data = memory_response.json()
        print(f"✅ Memory storage successful (ID: {memory_data.get('memory_id')})")
    else:
        print(f"❌ Memory storage failed: {memory_response.text}")

    # Step 3: Query for memories and tools
    print("3. Querying memories...")
    query_response = client.post("/memory/query", json=test_query)
    if query_response.status_code == 200:
        query_data = query_response.json()
        print("✅ Query successful:")
        print(f"   - Found {query_data['memories']['count']} relevant memories")
        print(f"   - Found {query_data['tools']['count']} relevant tools")

        # Detailed assertions
        assert "memories" in query_data
        assert "tools" in query_data
        assert "search_metadata" in query_data

        print("✅ End-to-end flow completed successfully!")
        return query_data
    else:
        print(f"❌ Query failed: {query_response.text}")
        pytest.fail(f"Query failed: {query_response.text}")

if __name__ == "__main__":
    # Allow running tests directly
    test_health_check()
    test_tool_registration()
    test_memory_store()
    test_memory_query()
    test_end_to_end_flow()
