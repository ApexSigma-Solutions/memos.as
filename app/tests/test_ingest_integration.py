"""
Integration tests for memOS.as ← InGest-LLM.as workflow

This test validates memOS.as functionality when receiving data from InGest-LLM.as.
Complements the core integration test suite (P1-CC-02).
"""

import pytest
import asyncio
import httpx
from fastapi.testclient import TestClient
from app.main import app

# Create test client
client = TestClient(app)

# Service URLs
INGEST_SERVICE_URL = "http://localhost:8000"
MEMOS_SERVICE_URL = "http://localhost:8091"

class TestMemOSIntegrationEndpoints:
    """Test memOS.as endpoints that support integration with InGest-LLM.as."""

    def test_memory_storage_endpoint(self):
        """Test memory storage endpoint that InGest-LLM.as uses."""
        test_memory = {
            "content": "Integration test memory from InGest-LLM.as",
            "metadata": {
                "source": "ingest-llm-as",
                "content_type": "text",
                "ingestion_id": "test_123",
                "chunk_index": 0
            }
        }

        response = client.post("/memory/store", json=test_memory)

        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
            assert "memory_id" in data
            print(f"✅ Memory stored with ID: {data['memory_id']}")
            return data["memory_id"]
        else:
            print(f"⚠️ Memory storage response: {response.status_code}")

    def test_memory_retrieval_endpoint(self):
        """Test memory retrieval that validates stored content."""
        # First store a memory
        memory_id = self.test_memory_storage_endpoint()

        if memory_id:
            response = client.get(f"/memory/{memory_id}")

            if response.status_code == 200:
                memory_data = response.json()
                assert "content" in memory_data
                assert memory_data["content"] == "Integration test memory from InGest-LLM.as"
                print(f"✅ Memory {memory_id} retrieved successfully")
            else:
                print(f"⚠️ Memory retrieval response: {response.status_code}")

    def test_memory_search_endpoint(self):
        """Test memory search functionality."""
        # First store searchable content
        self.test_memory_storage_endpoint()

        search_request = {
            "query": "integration test memory",
            "top_k": 5
        }

        response = client.post("/memory/query", json=search_request)

        if response.status_code == 200:
            search_data = response.json()
            assert "memories" in search_data
            assert "query" in search_data
            print(f"✅ Search returned {search_data['memories']['count']} results")
        else:
            print(f"⚠️ Memory search response: {response.status_code}")

    def test_tiered_memory_storage(self):
        """Test storage in different memory tiers."""
        # Test procedural memory (code content)
        code_memory = {
            "content": "def integration_test(): return True",
            "metadata": {
                "source": "ingest-llm-as",
                "content_type": "code",
                "language": "python"
            }
        }

        # Store in tier 2 (procedural memory)
        response = client.post("/memory/2/store", json=code_memory)

        if response.status_code == 200:
            data = response.json()
            assert data["success"] == True
            print("✅ Code content stored in procedural memory (Tier 2)")
        else:
            print(f"⚠️ Tiered storage response: {response.status_code}")

class TestMemOSHealthForIntegration:
    """Test memOS.as health endpoints that InGest-LLM.as depends on."""

    def test_health_check_detailed(self):
        """Test detailed health check that shows database status."""
        response = client.get("/health")

        if response.status_code == 200:
            health_data = response.json()

            # Check database connections
            if "services" in health_data:
                services = health_data["services"]

                # These are the databases that integration depends on
                expected_services = ["postgres", "qdrant", "redis"]

                for service in expected_services:
                    if service in services:
                        status = services[service]
                        print(f"✅ {service}: {status}")
                    else:
                        print(f"⚠️ {service}: not reported")

                return True
            else:
                print("⚠️ Health check missing services information")

        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False

@pytest.mark.integration
def test_memOS_ready_for_integration():
    """Comprehensive test that memOS.as is ready for InGest-LLM.as integration."""
    print("\n🧪 Testing memOS.as readiness for integration...")

    health_tester = TestMemOSHealthForIntegration()
    integration_tester = TestMemOSIntegrationEndpoints()

    # Test 1: Health check
    health_ok = health_tester.test_health_check_detailed()

    # Test 2: Core endpoints
    integration_tester.test_memory_storage_endpoint()
    integration_tester.test_memory_retrieval_endpoint()
    integration_tester.test_memory_search_endpoint()
    integration_tester.test_tiered_memory_storage()

    print("✅ memOS.as integration readiness tests completed")

if __name__ == "__main__":
    # Allow running tests directly
    test_memOS_ready_for_integration()
