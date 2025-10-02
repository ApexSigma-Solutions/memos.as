from dagster import asset
from app.models import LLMCacheRequest, LLMCacheResponse
from apexsigma_core.models import AgentPersona, Task
from datetime import datetime


@asset(
    name="sample_llm_cache_asset",
    group_name="memos_as_cache",
    description="A sample asset that demonstrates LLM cache functionality and apexsigma-core model usage",
)
def sample_llm_cache_asset():
    """Create a sample LLM cache entry and demonstrate apexsigma-core model usage."""
    # Create a sample request
    request = LLMCacheRequest(
        model="gpt-3.5-turbo",
        prompt="What is the capital of France?",
        temperature=0.7,
        max_tokens=100,
        metadata={"source": "sample_asset", "created_at": datetime.now().isoformat()},
    )

    # Create a sample response
    response = LLMCacheResponse(
        model=request.model,
        prompt=request.prompt,
        response="The capital of France is Paris.",
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        cached_at=datetime.now().isoformat(),
        metadata=request.metadata,
        response_length=26,
        prompt_length=26,
    )

    # Demonstrate apexsigma-core model usage
    # Create an AgentPersona instance
    agent_persona = AgentPersona(
        name="SampleAgent",
        description="A sample agent for demonstrating core model usage",
        capabilities=["llm_cache", "data_processing"],
    )

    # Create a Task instance
    task = Task(
        id="task_001",
        title="Sample LLM Cache Task",
        description="Process and cache LLM responses for common queries",
        priority="medium",
        status="completed",
        dependencies=[],
    )

    # Return the response and core model instances as the asset materialization
    return {
        "llm_cache": response.model_dump(),
        "agent_persona": agent_persona.model_dump(),
        "task": task.model_dump(),
    }
