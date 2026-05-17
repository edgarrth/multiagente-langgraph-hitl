"""Agente Supervisor - orquesta el flujo de trabajo e HITL."""
from typing import Dict, Any
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SupervisorAgent:
    """Agente que supervisa el flujo de trabajo y coordina HITL."""
    
    def __init__(self):
        """Inicializa el agente supervisor."""
        logger.info("Agente Supervisor inicializado")
    
    def route_request(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Enruta la solicitud al agente apropiado basado en el análisis.
        
        Args:
            state: Estado actual del grafo
            
        Returns:
            Estado actualizado con la decisión de enrutamiento
        """
        requires_sql = state.get("requires_sql", False)
        
        if requires_sql:
            logger.info("Enrutando al Experto SQL")
            next_agent = "sql_expert"
        else:
            logger.info("Enrutando al Explicador (no se necesita SQL)")
            next_agent = "explainer"
        
        return {
            **state,
            "next_agent": next_agent
        }
    
    def finalize_response(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Finaliza la respuesta después de todas las aprobaciones.
        
        Args:
            state: Estado actual del grafo
            
        Returns:
            Estado actualizado con la respuesta final
        """
        draft = state.get("draft_response", "")
        feedback = state.get("human_feedback", "")
        
        # Aplica la retroalimentación humana si se proporciona
        if feedback:
            final = f"{draft}\n\n[Actualizado basado en retroalimentación: {feedback}]"
        else:
            final = draft
        
        logger.info("Respuesta finalizada")
        
        return {
            **state,
            "final_response": final,
            "next_agent": None
        }


# Instancia global
supervisor = SupervisorAgent()