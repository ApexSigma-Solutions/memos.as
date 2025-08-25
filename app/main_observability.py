"""
Enhanced memOS main application with comprehensive observability integration.
"""

import os
import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.observability import get_observability, ObservabilityService
from app.services.observability_decorators import (
    trace_llm_operation,
    trace_memory_operation,
    trace_user_session,
    ObservabilityContext,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager with observability setup."""
    # Startup
    obs = get_observability()
    obs.log_structured("info", "memOS application starting up")

    # Test Langfuse integration
    if obs.langfuse:
        obs.log_structured("info", "Langfuse observability active")
        # Create application startup event
        obs.trace_llm_call(
            model="system",
            input_text="memOS application startup",
            output_text="Application successfully initialized",
            operation="startup",
            metadata={"event": "application_startup"},
        )
        obs.flush_langfuse()
    else:
        obs.log_structured("warning", "Langfuse observability not available")

    yield

    # Shutdown
    obs.log_structured("info", "memOS application shutting down")
    if obs.langfuse:
        obs.flush_langfuse()


# Create FastAPI app with observability
app = FastAPI(
    title="memOS - Memory-Driven AI Assistant",
    description="Personal AI assistant with comprehensive observability",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize observability
obs_service = get_observability()
obs_service.instrument_fastapi(app)
obs_service.instrument_database_clients()


@app.get("/")
async def root():
    """Root endpoint with observability."""
    obs = get_observability()
    obs.log_structured("info", "Root endpoint accessed")
    return {
        "message": "memOS - Memory-Driven AI Assistant",
        "version": "1.0.0",
        "status": "operational",
        "observability": "enabled",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint with observability status."""
    obs = get_observability()
    return obs.health_check()


@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint."""
    obs = get_observability()
    return obs.get_metrics()


@app.post("/chat")
@trace_llm_operation(
    operation_name="chat_completion", model="gpt-4", include_io=True
)
async def chat_completion(
    message: str,
    user_id: str = "default",
    session_id: str = "default",
    obs: ObservabilityService = Depends(get_observability),
):
    """Chat completion with full observability tracking."""

    with ObservabilityContext("chat_interaction", user_id, session_id) as ctx:
        ctx.log_step("message_received", {"length": len(message)})

        # Simulate LLM processing
        response = f"Echo: {message}"

        ctx.log_step("response_generated", {"length": len(response)})

        # Record detailed memory operation
        obs.trace_memory_operation_detailed(
            operation="chat_completion",
            memory_content=message,
            user_id=user_id,
            metadata={
                "response_length": len(response),
                "session_id": session_id,
            },
        )

        return {
            "response": response,
            "user_id": user_id,
            "session_id": session_id,
            "observability": "tracked",
        }


@app.post("/memory/store")
@trace_memory_operation("memory_store")
async def store_memory(
    content: str,
    user_id: str = "default",
    obs: ObservabilityService = Depends(get_observability),
):
    """Store memory with observability tracking."""

    obs.log_structured(
        "info", "Storing memory", user_id=user_id, content_length=len(content)
    )

    # Simulate memory storage
    memory_id = f"mem_{hash(content) % 10000}"

    # Trace the operation with Langfuse
    obs.trace_memory_operation_detailed(
        operation="store",
        memory_content=content,
        user_id=user_id,
        metadata={"memory_id": memory_id, "storage_tier": "primary"},
    )

    obs.record_memory_operation("store", "success", tier="primary")

    return {"memory_id": memory_id, "status": "stored", "user_id": user_id}


@app.get("/memory/retrieve/{memory_id}")
@trace_memory_operation("memory_retrieve")
async def retrieve_memory(
    memory_id: str,
    user_id: str = "default",
    obs: ObservabilityService = Depends(get_observability),
):
    """Retrieve memory with observability tracking."""

    obs.log_structured(
        "info", "Retrieving memory", user_id=user_id, memory_id=memory_id
    )

    # Simulate memory retrieval
    memory_content = f"Retrieved memory content for {memory_id}"

    obs.trace_memory_operation_detailed(
        operation="retrieve",
        memory_content=memory_content,
        user_id=user_id,
        metadata={"memory_id": memory_id, "retrieval_method": "direct"},
    )

    obs.record_memory_operation("retrieve", "success", tier="primary")

    return {
        "memory_id": memory_id,
        "content": memory_content,
        "user_id": user_id,
    }


@app.post("/session/start")
@trace_user_session("session_start")
async def start_session(
    user_id: str,
    session_id: str = None,
    obs: ObservabilityService = Depends(get_observability),
):
    """Start user session with tracking."""

    if not session_id:
        session_id = f"sess_{hash(user_id + str(time.time())) % 10000}"

    obs.log_structured(
        "info", "Starting user session", user_id=user_id, session_id=session_id
    )

    # Create session trace
    obs.trace_user_session(
        user_id=user_id,
        session_id=session_id,
        action="session_start",
        metadata={"timestamp": time.time()},
    )

    return {
        "session_id": session_id,
        "user_id": user_id,
        "status": "started",
        "observability": "tracked",
    }


@app.post("/test/langfuse")
async def test_langfuse_integration(
    obs: ObservabilityService = Depends(get_observability),
):
    """Test endpoint for Langfuse integration."""

    if not obs.langfuse:
        raise HTTPException(status_code=503, detail="Langfuse not available")

    # Test authentication
    if not obs.langfuse.auth_check():
        raise HTTPException(
            status_code=503, detail="Langfuse authentication failed"
        )

    # Create test trace
    trace_id = obs.trace_llm_call(
        model="test-model",
        input_text="Testing Langfuse integration",
        output_text="Integration test successful",
        operation="integration_test",
        metadata={"test": True, "endpoint": "/test/langfuse"},
    )

    # Flush data
    obs.flush_langfuse()

    return {
        "status": "success",
        "langfuse_available": True,
        "trace_id": trace_id,
        "message": "Langfuse integration working perfectly!",
    }


@app.get("/observability/dashboard")
async def observability_dashboard():
    """Dashboard endpoint showing observability status."""
    obs = get_observability()

    health = obs.health_check()

    return {
        "service": health,
        "endpoints": {
            "metrics": "/metrics",
            "health": "/health",
            "langfuse_test": "/test/langfuse",
        },
        "monitoring": {
            "prometheus": "http://localhost:9090",
            "grafana": "http://localhost:3000",
            "jaeger": "http://localhost:16686",
            "langfuse": "https://cloud.langfuse.com",
        },
    }


if __name__ == "__main__":
    import uvicorn

    print("🚀 Starting memOS with comprehensive observability...")
    print("📊 Monitoring endpoints:")
    print("   - Health: http://localhost:8090/health")
    print("   - Metrics: http://localhost:8090/metrics")
    print("   - Dashboard: http://localhost:8090/observability/dashboard")
    print("   - Langfuse Test: http://localhost:8090/test/langfuse")

    uvicorn.run(
        "main:app", host="0.0.0.0", port=8090, reload=True, log_level="info"
    )
