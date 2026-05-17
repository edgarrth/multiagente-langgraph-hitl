"""Memoria a corto plazo (contexto de conversación)."""
from typing import List, Dict, Any
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ShortTermMemory:
    """Gestiona la memoria de conversación a corto plazo (almacenada en el estado del grafo)."""
    
    @staticmethod
    def format_messages_for_context(
        messages: List[Dict[str, str]],
        max_messages: int = 10
    ) -> str:
        """Formatea mensajes recientes para el contexto del LLM.
        
        Args:
            messages: Lista de diccionarios de mensajes
            max_messages: Número máximo de mensajes a incluir
            
        Returns:
            Cadena formateada de mensajes recientes
        """
        recent = messages[-max_messages:]
        formatted = []
        
        for msg in recent:
            role = msg.get("role", "desconocido")
            content = msg.get("content", "")
            formatted.append(f"{role.upper()}: {content}")
        
        return "\n".join(formatted)
    
    @staticmethod
    def summarize_conversation(messages: List[Dict[str, str]]) -> str:
        """Crea un breve resumen de la conversación.
        
        Args:
            messages: Lista de diccionarios de mensajes
            
        Returns:
            Cadena de resumen
        """
        if not messages:
            return "Sin historial de conversación"
        
        # Resumen heurístico simple
        user_messages = [m["content"] for m in messages if m.get("role") == "user"]
        topics = ", ".join(user_messages[:3])
        
        return f"Conversation about: {topics} ({len(messages)} messages total)"