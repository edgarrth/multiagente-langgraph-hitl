"""Agente Intérprete de Consultas - analiza la intención del usuario."""
from typing import Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class QueryInterpreterAgent:
    """Agente que interpreta las consultas del usuario y determina su intención."""
    
    def __init__(self):
        """Inicializa el agente intérprete de consultas."""
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            api_key=settings.openai_api_key
        )
        logger.info("Agente Intérprete de Consultas inicializado")
    
    def analyze_query(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Analiza la consulta del usuario para determinar su intención y requisitos.
        
        Args:
            state: Estado actual del grafo
            
        Returns:
            Estado actualizado con el análisis de la consulta
        """
        user_query = state["user_query"]
        logger.info(f"Analizando consulta: {user_query}")
        
        system_prompt = """Eres un analizador de consultas para una base de datos de tienda de música (Chinook).
        
Analiza la pregunta del usuario y determina:
1. La intención (p. ej., 'análisis_de_ventas', 'información_de_cliente', 'búsqueda_de_producto', 'pregunta_general')
2. Si requiere una consulta SQL (verdadero/falso)
3. Entidades o conceptos clave mencionados

Responde en este formato exacto:
INTENCION: <tipo_intención>
REQUIERE_SQL: <verdadero/falso>
ENTIDADES: <lista_separada_por_comas>
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Pregunta del usuario: {user_query}")
        ]
        
        response = self.llm.invoke(messages)
        analysis = response.content
        
        # Analizar respuesta
        intent = "general"
        requires_sql = False
        
        for line in analysis.split("\n"):
            if line.startswith("INTENCION:"):
                intent = line.split(":", 1)[1].strip()
            elif line.startswith("REQUIERE_SQL:"):
                requires_sql = line.split(":", 1)[1].strip().lower() in ["verdadero", "true"]
        
        logger.info(f"Análisis de consulta - Intención: {intent}, Requiere SQL: {requires_sql}")
        
        return {
            **state,
            "query_intent": intent,
            "requires_sql": requires_sql,
            "next_agent": "supervisor"
        }


# Instancia global
query_interpreter = QueryInterpreterAgent()