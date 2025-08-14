from pydantic import BaseModel
from typing import Optional, List, Dict, Any

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
