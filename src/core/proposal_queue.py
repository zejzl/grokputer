from __future__ import annotations

import json
from typing import Dict, List, Optional

import redis

from src.config import config  # For Redis URL


class ProposalQueue:
    """
    Redis-backed queue for Taskmaster proposals.
    Stores proposals as JSON in a Redis hash for persistence.
    """

    def __init__(self, redis_url: str = None):
        self.redis_url = redis_url or config.get("REDIS_URL", "redis://localhost:6379")
        self.redis_client = redis.from_url(self.redis_url)
        self.key = "taskmaster_proposals"  # Redis key for hash

    def add_proposal(self, proposal: Dict) -> str:
        """Add a proposal to the queue. Returns ID."""
        proposal_id = f"prop_{len(self.get_all()) + 1}"
        proposal["id"] = proposal_id
        self.redis_client.hset(self.key, proposal_id, json.dumps(proposal))
        return proposal_id

    def get_all(self) -> List[Dict]:
        """Get all queued proposals."""
        proposals = self.redis_client.hgetall(self.key)
        return [json.loads(v) for v in proposals.values()] if proposals else []

    def get_proposal(self, proposal_id: str) -> Optional[Dict]:
        """Get specific proposal."""
        data = self.redis_client.hget(self.key, proposal_id)
        return json.loads(data) if data else None

    def size(self) -> int:
        """Queue size."""
        return len(self.redis_client.hkeys(self.key))

    def approve_proposal(self, proposal_id: str, approved: bool = True):
        """Mark proposal as approved/rejected."""
        proposal = self.get_proposal(proposal_id)
        if proposal:
            proposal["status"] = "approved" if approved else "rejected"
            proposal["timestamp_approved"] = json.dumps({"time": "now"})
            self.redis_client.hset(self.key, proposal_id, json.dumps(proposal))

    def remove_proposal(self, proposal_id: str):
        """Remove from queue."""
        self.redis_client.hdel(self.key, proposal_id)

    def clear_queue(self):
        """Clear all proposals."""
        self.redis_client.delete(self.key)
