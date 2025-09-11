from enum import Enum
from pydantic import BaseModel


class MCPTier(str, Enum):
    MCP_GEMINI = "mcp_gemini"
    MCP_COPILOT = "mcp_copilot"
    MCP_QWEN = "mcp_qwen"
    MCP_SYSTEM = "mcp_system"


class MemoryTier(str, Enum):
    WORKING = "1"
    PROCEDURAL = "2"
    SEMANTIC = "3"


MCP_TIER_MAPPING = {
    MCPTier.MCP_GEMINI: MemoryTier.PROCEDURAL,  # Maps to Tier 2
    MCPTier.MCP_COPILOT: MemoryTier.PROCEDURAL,
    MCPTier.MCP_QWEN: MemoryTier.PROCEDURAL,
    MCPTier.MCP_SYSTEM: MemoryTier.SEMANTIC,  # Maps to Tier 3
}


class KnowledgeShareRequest(BaseModel):
    agent_id: str
    target_agent: str
    query: str
    confidence_threshold: float = 0.8
    sharing_policy: str = "high_confidence_only"


class KnowledgeShareOffer(BaseModel):
    request_id: int
    offering_agent_id: str
    memory_id: int
    confidence_score: float
