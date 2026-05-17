"""Memoria a largo plazo (persistente en Supabase)."""
from typing import List, Dict, Any, Optional
from src.db.supabase_manager import supabase_manager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class LongTermMemory:
    """Gestiona memoria persistente a largo plazo en Supabase."""
    
    def __init__(self):
        """Inicializa LTM con el gestor de Supabase."""
        self.db = supabase_manager
    
    def store_insight(
        self,
        user_id: str,
        insight: str,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Guarda un insight o descubrimiento importante.
        
        Args:
            user_id: Identificador del usuario
            insight: Texto del insight
            context: Información de contexto opcional
        """
        self.db.save_memory(
            user_id=user_id,
            memory_type="insight",
            content=insight,
            metadata=context
        )
        logger.info(f"Insight almacenado para el usuario {user_id}")
    
    def store_preference(
        self,
        user_id: str,
        preference: str,
        value: str
    ) -> None:
        """Guarda una preferencia del usuario.
        
        Args:
            user_id: Identificador del usuario
            preference: Nombre de la preferencia
            value: Valor de la preferencia
        """
        self.db.save_memory(
            user_id=user_id,
            memory_type="preference",
            content=f"{preference}: {value}",
            metadata={"preference": preference, "value": value}
        )
        logger.info(f"Stored preference for user {user_id}")
    
    def retrieve_relevant_memories(
        self,
        user_id: str,
        query_context: str,
        limit: int = 5
    ) -> List[str]:
        """Recupera las memorias relevantes para el contexto actual.
        
        Args:
            user_id: Identificador del usuario
            query_context: Consulta o contexto actual
            limit: Máximo de memorias a recuperar
            
        Returns:
            Lista de cadenas de memoria relevantes
        """
        # Recupera memorias recientes (podría mejorarse con búsqueda vectorial)
        memories = self.db.get_user_memories(user_id, limit=limit)
        
        # Simple filtering (could use embeddings/similarity in production)
        relevant = []
        for mem in memories:
            content = mem.get("content", "")
            if content:
                relevant.append(f"[{mem['memory_type']}] {content}")
        
        logger.info(f"Retrieved {len(relevant)} relevant memories")
        return relevant
    
    def save_conversation_summary(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[Dict[str, str]],
        summary: str
    ) -> None:
        """Guarda la conversación con resumen en LTM.
        
        Args:
            user_id: Identificador del usuario
            conversation_id: Identificador de la conversación
            messages: Mensajes de la conversación
            summary: Resumen de la conversación
        """
        self.db.save_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
            messages=messages,
            metadata={"summary": summary}
        )
        logger.info(f"Saved conversation summary {conversation_id}")


# Global instance
ltm = LongTermMemory()