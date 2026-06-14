"""Memoria a largo plazo persistente en SQLite local."""
from typing import List, Dict, Any, Optional
from src.db.local_memory_manager import local_memory_manager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class LongTermMemory:
    """Gestiona memoria persistente local a largo plazo."""

    def __init__(self):
        self.db = local_memory_manager

    def store_insight(self, user_id: str, insight: str, context: Optional[Dict[str, Any]] = None) -> None:
        self.db.save_memory(user_id=user_id, memory_type="insight", content=insight, metadata=context)
        logger.info("Insight almacenado para el usuario %s", user_id)

    def store_preference(self, user_id: str, preference: str, value: str) -> None:
        self.db.save_memory(
            user_id=user_id,
            memory_type="preference",
            content=f"{preference}: {value}",
            metadata={"preference": preference, "value": value},
        )
        logger.info("Preferencia almacenada para el usuario %s", user_id)

    def retrieve_relevant_memories(self, user_id: str, query_context: str, limit: int = 5) -> List[str]:
        memories = self.db.get_user_memories(user_id, limit=limit)
        relevant = []
        for mem in memories:
            content = mem.get("content", "")
            if content:
                relevant.append(f"[{mem['memory_type']}] {content}")
        logger.info("Retrieved %s relevant memories", len(relevant))
        return relevant

    def save_conversation_summary(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[Dict[str, str]],
        summary: str,
    ) -> None:
        self.db.save_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            messages=messages,
            metadata={"summary": summary},
        )
        logger.info("Saved conversation summary %s", conversation_id)


ltm = LongTermMemory()
