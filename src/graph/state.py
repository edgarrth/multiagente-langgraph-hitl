"""Definición del estado del grafo para el sistema multiagente."""
from typing import TypedDict, List, Dict, Any, Optional, Annotated
from langgraph.graph import add_messages


class AgentState(TypedDict):
    """Estado para el grafo multiagente."""
    
    # Conversación
    messages: Annotated[List[Dict[str, str]], add_messages]
    
    # Contexto del usuario
    user_id: str
    conversation_id: str
    
    # Análisis de consulta
    user_query: str
    query_intent: Optional[str]
    requires_sql: bool
    
    # Generación y ejecución de SQL
    generated_sql: Optional[str]
    sql_approved: bool
    sql_results: Optional[List[Dict[str, Any]]]
    
    # Generación de respuesta
    draft_response: Optional[str]
    response_approved: bool
    final_response: Optional[str]
    
    # Memoria
    ltm_context: List[str]
    
    # Flujo de control
    next_agent: Optional[str]
    human_feedback: Optional[str]
    iteration_count: int