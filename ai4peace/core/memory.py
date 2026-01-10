"""Memory store for RAG-based agent memory."""

from typing import List, Dict, Optional
from datetime import datetime
import json


class MemoryStore:
    """Simple memory store for agent actions and messages.
    
    Can be extended with vector embeddings for semantic search.
    """
    
    def __init__(self):
        """Initialize an empty memory store."""
        self.memories: List[Dict] = []
    
    def add_memory(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        timestamp: Optional[datetime] = None,
    ):
        """Add a memory to the store."""
        memory = {
            "content": content,
            "metadata": metadata or {},
            "timestamp": timestamp or datetime.now(),
        }
        self.memories.append(memory)
    
    def search(
        self,
        query: str,
        limit: int = 10,
        character_name: Optional[str] = None,
    ) -> List[Dict]:
        """Search memories by keyword matching.
        
        Can be extended with vector similarity search.
        """
        results = []
        query_lower = query.lower()
        
        for memory in self.memories:
            if query_lower in memory["content"].lower():
                if character_name is None or memory["metadata"].get("character") == character_name:
                    results.append(memory)
        
        return results[:limit]
    
    def get_recent(
        self,
        limit: int = 10,
        character_name: Optional[str] = None,
    ) -> List[Dict]:
        """Get recent memories."""
        results = self.memories
        if character_name:
            results = [m for m in results if m["metadata"].get("character") == character_name]
        return sorted(results, key=lambda x: x["timestamp"], reverse=True)[:limit]

