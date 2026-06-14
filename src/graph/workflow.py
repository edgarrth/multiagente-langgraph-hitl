"""LangGraph workflow definition.

Este módulo contiene la orquestación real de la PoC. La UI y el CLI ya no
llaman a los agentes de forma procedural; invocan este grafo compilado.
"""
from __future__ import annotations

from pathlib import Path
from typing import Literal

from langgraph.graph import StateGraph, END

from src.agents.query_interpreter import query_interpreter
from src.agents.sql_expert import sql_expert
from src.agents.explainer import explainer
from src.agents.supervisor import supervisor
from src.config.settings import settings
from src.graph.state import AgentState
from src.memory.long_term import ltm
from src.memory.short_term import ShortTermMemory
from src.db.redis_manager import redis_manager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def sql_review_node(state: AgentState) -> AgentState:
    """Nodo HITL para aprobación de SQL.

    En Streamlit/API no bloquea el proceso: marca el estado como pendiente y
    termina el grafo. Cuando el usuario aprueba/edita, la UI vuelve a invocar
    el grafo con `sql_override` o `auto_approve_sql=True`.
    """
    if state.get("sql_rejected"):
        return {
            **state,
            "final_response": "Consulta SQL rechazada.",
            "status": "rejected",
            "pending_approval": None,
        }

    if state.get("sql_override"):
        return {
            **state,
            "generated_sql": state.get("sql_override"),
            "sql_approved": True,
            "status": "running",
            "pending_approval": None,
        }

    if state.get("auto_approve_sql"):
        return {
            **state,
            "sql_approved": True,
            "status": "running",
            "pending_approval": None,
        }

    return {
        **state,
        "sql_approved": False,
        "status": "waiting_for_sql_approval",
        "pending_approval": "sql",
        "final_response": "SQL pendiente aprobación.",
    }


def response_review_node(state: AgentState) -> AgentState:
    """Nodo HITL para aprobación de respuesta final."""
    if state.get("response_rejected"):
        return {
            **state,
            "final_response": "Respuesta rechazada.",
            "status": "rejected",
            "pending_approval": None,
        }

    if state.get("human_feedback"):
        return {
            **state,
            "response_approved": True,
            "status": "running",
            "pending_approval": None,
        }

    if state.get("auto_approve_response"):
        return {
            **state,
            "response_approved": True,
            "status": "running",
            "pending_approval": None,
        }

    return {
        **state,
        "response_approved": False,
        "status": "waiting_for_response_approval",
        "pending_approval": "response",
        "final_response": state.get("draft_response"),
    }


def finalizer_node(state: AgentState) -> AgentState:
    """Finaliza la respuesta y guarda memoria local."""
    state = supervisor.finalize_response(state)

    user_id = state.get("user_id", "usuario_demo")
    conversation_id = state.get("conversation_id", "unknown")
    final_response = state.get("final_response") or ""
    messages = list(state.get("messages") or [])
    messages.append({"role": "assistant", "content": final_response})

    try:
        summary = ShortTermMemory.summarize_conversation(messages)
        ltm.save_conversation_summary(user_id, conversation_id, messages, summary)
        if final_response:
            ltm.store_insight(
                user_id,
                insight=f"Pregunta: {state.get('user_query')} | Respuesta: {final_response[:500]}",
                context={"conversation_id": conversation_id, "intent": state.get("query_intent")},
            )
    except Exception as exc:
        logger.warning("No se pudo guardar memoria local: %s", exc)

    redis_manager.publish_event(
        "langgraph_events",
        {
            "type": "conversation_completed",
            "conversation_id": conversation_id,
            "user_id": user_id,
            "status": "completed",
        },
    )

    return {
        **state,
        "messages": messages,
        "status": "completed",
        "pending_approval": None,
    }


def route_from_supervisor(state: AgentState) -> Literal["sql_expert", "explainer"]:
    return "sql_expert" if state.get("requires_sql", False) else "explainer"


def route_after_sql_expert(state: AgentState) -> Literal["explainer", "human_sql_review"]:
    # Consultas de schema o NO_SQL_POSIBLE ya dejan resultados/respuesta preparados.
    if state.get("sql_results") is not None or state.get("draft_response"):
        return "explainer"
    return "human_sql_review"


def route_after_sql_review(state: AgentState) -> Literal["sql_executor", "end"]:
    if state.get("sql_approved"):
        return "sql_executor"
    return "end"


def route_after_response_review(state: AgentState) -> Literal["finalizer", "end"]:
    if state.get("response_approved"):
        return "finalizer"
    return "end"


def create_checkpointer():
    """Crea checkpointer local si la dependencia está disponible."""
    checkpoint_path = Path(settings.langgraph_checkpoint_db_path)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        import sqlite3

        conn = sqlite3.connect(str(checkpoint_path), check_same_thread=False)
        logger.info("SqliteSaver inicializado en %s", checkpoint_path)
        return SqliteSaver(conn)
    except Exception as exc:
        from langgraph.checkpoint.memory import MemorySaver

        logger.warning("Usando MemorySaver; no se pudo inicializar SqliteSaver: %s", exc)
        return MemorySaver()


def create_workflow():
    """Crea y compila el grafo multiagente."""
    workflow = StateGraph(AgentState)

    workflow.add_node("query_interpreter", query_interpreter.analyze_query)
    workflow.add_node("supervisor", supervisor.route_request)
    workflow.add_node("sql_expert", sql_expert.generate_sql)
    workflow.add_node("human_sql_review", sql_review_node)
    workflow.add_node("sql_executor", sql_expert.execute_sql)
    workflow.add_node("explainer", explainer.explain_results)
    workflow.add_node("human_response_review", response_review_node)
    workflow.add_node("finalizer", finalizer_node)

    workflow.set_entry_point("query_interpreter")
    workflow.add_edge("query_interpreter", "supervisor")

    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {"sql_expert": "sql_expert", "explainer": "explainer"},
    )
    workflow.add_conditional_edges(
        "sql_expert",
        route_after_sql_expert,
        {"human_sql_review": "human_sql_review", "explainer": "explainer"},
    )
    workflow.add_conditional_edges(
        "human_sql_review",
        route_after_sql_review,
        {"sql_executor": "sql_executor", "end": END},
    )
    workflow.add_edge("sql_executor", "explainer")
    workflow.add_edge("explainer", "human_response_review")
    workflow.add_conditional_edges(
        "human_response_review",
        route_after_response_review,
        {"finalizer": "finalizer", "end": END},
    )
    workflow.add_edge("finalizer", END)

    app = workflow.compile(checkpointer=create_checkpointer())
    logger.info("Grafo LangGraph compilado")
    return app


workflow_app = create_workflow()
