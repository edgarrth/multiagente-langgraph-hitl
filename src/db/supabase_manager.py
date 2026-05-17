"""Supabase PostgreSQL connection for long-term memory."""
from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from supabase import create_client, Client
from src.config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SupabaseManager:
    """Manager for Supabase operations (LTM storage)."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.client: Client = create_client(
            settings.supabase_url,
            settings.supabase_service_role_key
        )
        logger.info("Gestor de Supabase inicializado")
    
    def _serialize_messages(self, messages: List[Any]) -> str:
        """Serialize messages to JSON, handling LangChain message objects.
        
        Args:
            messages: List of messages (dicts or LangChain objects)
            
        Returns:
            JSON string
        """
        serialized = []
        for msg in messages:
            if isinstance(msg, dict):
                serialized.append(msg)
            else:
                # Handle LangChain message objects (HumanMessage, AIMessage, etc.)
                try:
                    serialized.append({
                        "role": getattr(msg, 'type', 'unknown'),
                        "content": getattr(msg, 'content', str(msg))
                    })
                except Exception as e:
                    logger.warning(f"  Error serializando mensaje: {e}")
                    serialized.append({"role": "unknown", "content": str(msg)})
        
        return json.dumps(serialized)
    
    def save_conversation(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Save conversation to long-term memory.
        
        Args:
            user_id: User identifier
            conversation_id: Conversation identifier
            messages: List of message dictionaries or objects
            metadata: Optional metadata
            
        Returns:
            Saved conversation record
        """
        try:
            data = {
                "user_id": user_id,
                "conversation_id": conversation_id,
                "messages": self._serialize_messages(messages),
                "metadata": json.dumps(metadata or {}),
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table("conversations").insert(data).execute()
            logger.info(f" Conversación {conversation_id} guardada en Supabase")
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f" Error guardando conversación en Supabase: {e}")
            return {}
    
    def save_memory(
        self,
        user_id: str,
        memory_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Save a memory item.
        
        Args:
            user_id: User identifier
            memory_type: Type of memory (e.g., 'insight', 'preference')
            content: Memory content
            metadata: Optional metadata
            
        Returns:
            Saved memory record
        """
        try:
            data = {
                "user_id": user_id,
                "memory_type": memory_type,
                "content": content,
                "metadata": json.dumps(metadata or {}),
                "created_at": datetime.utcnow().isoformat()
            }
            
            result = self.client.table("memories").insert(data).execute()
            logger.info(f" Memoria guardada - Tipo: {memory_type}")
            return result.data[0] if result.data else {}
        except Exception as e:
            logger.error(f" Error guardando memoria en Supabase: {e}")
            return {}
    
    def get_user_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve user memories.
        
        Args:
            user_id: User identifier
            memory_type: Optional filter by memory type
            limit: Maximum number of memories to retrieve
            
        Returns:
            List of memory records
        """
        try:
            query = self.client.table("memories").select("*").eq("user_id", user_id)
            
            if memory_type:
                query = query.eq("memory_type", memory_type)
            
            result = query.order("created_at", desc=True).limit(limit).execute()
            logger.info(f"Retrieved {len(result.data)} memories for user {user_id}")
            return result.data
        except Exception as e:
            logger.error(f" Error obteniendo memorias: {e}")
            return []
    
    def get_conversation_history(
        self,
        user_id: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Retrieve recent conversation history.
        
        Args:
            user_id: User identifier
            limit: Maximum number of conversations
            
        Returns:
            List of conversation records
        """
        try:
            result = (
                self.client.table("conversations")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            logger.info(f"Retrieved {len(result.data)} conversations for user {user_id}")
            return result.data
        except Exception as e:
            logger.error(f" Error obteniendo historial: {e}")
            return []


# Global instance
supabase_manager = SupabaseManager()