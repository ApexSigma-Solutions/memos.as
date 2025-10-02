from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime


class AgentPersona(BaseModel):
    name: str
    description: str
    capabilities: List[str]


class Task(BaseModel):
    id: str
    title: str
    description: str
    priority: str
    dependencies: List[str] = Field(default_factory=list)
    status: str
    subtasks: List["Task"] = Field(default_factory=list)


class StoreRequest(BaseModel):
    content: str
    metadata: Optional[Dict[str, Any]] = None
    agent_id: Optional[str] = "default_agent"
    expires_at: Optional[datetime] = None


class QueryRequest(BaseModel):
    query: str
    top_k: Optional[int] = 5
    agent_id: Optional[str] = "default_agent"
