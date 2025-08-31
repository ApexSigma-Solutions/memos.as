from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class StoreRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5


class ToolRegistrationRequest(BaseModel):
    name: str
    description: str
    usage: str
    tags: Optional[List[str]] = None


class GraphQueryRequest(BaseModel):
    node_label: str
    filters: Dict[str, Any] = {}
    return_properties: Optional[List[str]] = None


# LLM Cache Models
class LLMCacheRequest(BaseModel):
    model: str
    prompt: str
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 1000
    metadata: Optional[Dict[str, Any]] = None


class LLMCacheResponse(BaseModel):
    model: str
    prompt: str
    response: str
    temperature: float
    max_tokens: int
    cached_at: str
    metadata: Optional[Dict[str, Any]] = None
    response_length: int
    prompt_length: int


class LLMUsageRequest(BaseModel):
    model: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    request_id: Optional[str] = None


class LLMUsageStats(BaseModel):
    model: str
    total_requests: int
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int


class LLMPerformanceRequest(BaseModel):
    model: str
    operation: str
    response_time: float
    success: Optional[bool] = True
    error_message: Optional[str] = None


class LLMPerformanceStats(BaseModel):
    model: str
    operation: str
    success_rate: float
    avg_response_time: float
    min_response_time: float
    max_response_time: float
    sample_size: int
