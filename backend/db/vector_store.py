"""
AutoForge Vector Store — ChromaDB-backed semantic similarity search.

Provides:
- Embedding storage for agent experiences and skills
- Semantic similarity search for memory recall
- Graceful fallback when ChromaDB is unavailable
- Lightweight text embedding via sentence hashing (no heavy ML model)
"""

import hashlib
import json
import logging
from typing import Any, Dict, List, Optional

from config import settings

log = logging.getLogger("autoforge.db.vector_store")

_client = None
_collection = None
_available = False


async def init_vector_store():
    """Connect to ChromaDB and get/create the memory collection."""
    global _client, _collection, _available
    try:
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        _client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        # Verify connectivity
        _client.heartbeat()

        _collection = _client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        _available = True
        log.info("vector_store_connected: host=%s port=%s collection=%s",
                 settings.CHROMA_HOST, settings.CHROMA_PORT, settings.CHROMA_COLLECTION)
    except Exception as exc:
        _available = False
        _client = None
        _collection = None
        log.warning("vector_store_unavailable: %s — falling back to keyword recall", str(exc))


def is_available() -> bool:
    """Check if the vector store is connected."""
    return _available


def _text_to_document(experience: Dict[str, Any]) -> str:
    """Convert an experience dict to a searchable text document."""
    parts = [
        f"agent:{experience.get('agent_type', '')}",
        f"failure:{experience.get('failure_type', '')}",
        f"action:{experience.get('action_taken', '')}",
        f"outcome:{'success' if experience.get('success') else 'failure'}",
        experience.get("context_summary", ""),
        experience.get("reusable_skill", ""),
    ]
    return " ".join(p for p in parts if p)


async def store_experience(experience_id: str, experience: Dict[str, Any]):
    """Store an experience embedding in the vector store."""
    if not _available or _collection is None:
        return
    try:
        doc = _text_to_document(experience)
        metadata = {
            "agent_type": experience.get("agent_type", ""),
            "failure_type": experience.get("failure_type", ""),
            "success": str(experience.get("success", False)),
            "confidence": float(experience.get("confidence", 0.0)),
            "action_taken": experience.get("action_taken", ""),
            "reusable_skill": experience.get("reusable_skill", "") or "",
        }
        _collection.upsert(
            ids=[experience_id],
            documents=[doc],
            metadatas=[metadata],
        )
    except Exception as exc:
        log.warning("vector_store_insert_failed: %s", str(exc))


async def store_skill(skill_id: str, skill: Dict[str, Any]):
    """Store a skill embedding in the vector store."""
    if not _available or _collection is None:
        return
    try:
        doc = (
            f"skill:{skill.get('name', '')} "
            f"agent:{skill.get('agent_type', '')} "
            f"{skill.get('description', '')}"
        )
        metadata = {
            "agent_type": skill.get("agent_type", ""),
            "type": "skill",
            "name": skill.get("name", ""),
            "success_rate": float(skill.get("success_count", 0)) / max(skill.get("usage_count", 1), 1),
        }
        _collection.upsert(
            ids=[f"skill:{skill_id}"],
            documents=[doc],
            metadatas=[metadata],
        )
    except Exception as exc:
        log.warning("vector_store_skill_insert_failed: %s", str(exc))


async def search_similar(
    query: str,
    agent_type: Optional[str] = None,
    n_results: int = 5,
    failure_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Semantic similarity search for experiences/skills.

    Args:
        query: Natural-language query (error logs, context description).
        agent_type: Optional filter by agent.
        n_results: Max results.
        failure_type: Optional filter by failure type.

    Returns:
        List of matching documents with metadata and distance scores.
    """
    if not _available or _collection is None:
        return []
    try:
        where_filter = None
        conditions = []
        if agent_type:
            conditions.append({"agent_type": agent_type})
        if failure_type:
            conditions.append({"failure_type": failure_type})

        if len(conditions) == 1:
            where_filter = conditions[0]
        elif len(conditions) > 1:
            where_filter = {"$and": conditions}

        results = _collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where_filter,
            include=["documents", "metadatas", "distances"],
        )

        matches = []
        ids = results.get("ids", [[]])[0]
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for i, doc_id in enumerate(ids):
            matches.append({
                "id": doc_id,
                "document": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distances[i] if i < len(distances) else 1.0,
                "similarity": 1.0 - (distances[i] if i < len(distances) else 1.0),
            })

        return matches
    except Exception as exc:
        log.warning("vector_store_search_failed: %s", str(exc))
        return []


async def get_collection_stats() -> Dict[str, Any]:
    """Get vector store stats."""
    if not _available or _collection is None:
        return {"available": False, "count": 0}
    try:
        count = _collection.count()
        return {"available": True, "count": count, "collection": settings.CHROMA_COLLECTION}
    except Exception:
        return {"available": False, "count": 0}
