"""Definición del estado del grafo para el sistema multiagente."""
from typing import TypedDict, List, Dict, Any, Optional


class AgentState(TypedDict, total=False):
    """Estado compartido por todos los nodos LangGraph."""

    # Conversación
    messages: List[Dict[str, str]]

    # Contexto del usuario
    user_id: str
    conversation_id: str
    user_query: str

    # Análisis de consulta
    query_intent: Optional[str]
    requires_sql: bool

    # Generación y ejecución de SQL
    generated_sql: Optional[str]
    sql_approved: bool
    sql_results: Optional[List[Dict[str, Any]]]
    sql_override: Optional[str]
    sql_rejected: bool

    # Generación de respuesta
    draft_response: Optional[str]
    response_approved: bool
    response_rejected: bool
    final_response: Optional[str]

    # Memoria
    ltm_context: List[str]

    # Control HITL / runtime
    interactive: bool
    auto_approve_sql: bool
    auto_approve_response: bool
    human_feedback: Optional[str]
    next_agent: Optional[str]
    status: Optional[str]
    pending_approval: Optional[str]
    iteration_count: int
