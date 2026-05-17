"""Explainer Agent - transforms technical results into friendly responses."""
from typing import Dict, Any, List
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class ExplainerAgent:
    """Agent that explains technical results in user-friendly language."""
    
    def __init__(self):
        """Initialize explainer agent."""
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            api_key=settings.openai_api_key
        )
        logger.info("Agente Explicador inicializado")
    
    def explain_results(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate user-friendly explanation of query results.
        
        Args:
            state: Current graph state
            
        Returns:
            Updated state with draft response
        """
        user_query = state["user_query"]
        sql_results = state.get("sql_results")
        
        logger.info("Generando explicación para los resultados")
        
        if not sql_results:
            return {
                **state,
                "draft_response": "No pude encontrar datos para responder tu pregunta.",
                "response_approved": False,
                "next_agent": "hitl_response_review"
            }
        
        # Caso especial: listado de tablas
        if all('tabla' in row for row in sql_results):
            tables = [row['tabla'] for row in sql_results]
            explanation = f"La base de datos Chinook contiene {len(tables)} tablas:\n\n"
            explanation += "\n".join([f"• {table}" for table in tables])
            
            logger.info(f" Explicación de esquema generada ({len(tables)} tablas)")
            
            return {
                **state,
                "draft_response": explanation,
                "response_approved": False,
                "next_agent": "hitl_response_review"
            }
        
        system_prompt = """Eres un asistente útil que explica resultados de consultas de bases de datos.

Transforma los resultados técnicos en respuestas claras y conversacionales.
- Sé conciso pero informativo
- Destaca los insights clave
- Usa lenguaje natural, no jerga técnica
- Si los datos muestran tendencias o patrones, menciόnalos
- Responde en español
"""
        
        # Format results for context
        results_text = f"Resultados de la Consulta ({len(sql_results)} filas):\n"
        for i, row in enumerate(sql_results[:10], 1):  # Show max 10 rows
            results_text += f"{i}. {row}\n"
        
        if len(sql_results) > 10:
            results_text += f"... y {len(sql_results) - 10} filas más"
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"""Pregunta del Usuario: {user_query}

{results_text}

Proporciona una explicación clara y amigable de estos resultados.""")
        ]
        
        response = self.llm.invoke(messages)
        explanation = response.content
        
        logger.info(" Explicación generada exitosamente")
        
        return {
            **state,
            "draft_response": explanation,
            "response_approved": False,
            "next_agent": "hitl_response_review"
        }


# Global instance
explainer = ExplainerAgent()