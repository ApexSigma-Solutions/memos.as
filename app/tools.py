import requests
from app.schemas import KnowledgeShareRequest, KnowledgeShareOffer

BASE_URL = "http://localhost:8091"

def request_knowledge_from_agent(agent_id: str, target_agent_id: str, query: str, confidence_threshold: float = 0.8, sharing_policy: str = "high_confidence_only"):
    url = f"{BASE_URL}/memory/share/request"
    payload = {
        "agent_id": agent_id,
        "target_agent": target_agent_id,
        "query": query,
        "confidence_threshold": confidence_threshold,
        "sharing_policy": sharing_policy,
    }
    response = requests.post(url, json=payload)
    return response.json()

def share_knowledge_with_agent(request_id: int, offering_agent_id: str, memory_id: int, confidence_score: float):
    url = f"{BASE_URL}/memory/share/offer"
    payload = {
        "request_id": request_id,
        "offering_agent_id": offering_agent_id,
        "memory_id": memory_id,
        "confidence_score": confidence_score,
    }
    response = requests.post(url, json=payload)
    return response.json()

def get_pending_knowledge_requests(agent_id: str):
    url = f"{BASE_URL}/memory/share/pending?agent_id={agent_id}"
    response = requests.get(url)
    return response.json()