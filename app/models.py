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
