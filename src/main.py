"""Main entry point for the multiagent LangGraph system."""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional

from src.graph.workflow import workflow_app
from src.memory.long_term import ltm
from src.db.redis_manager import redis_manager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def _normalize_yes_no(value: str) -> str:
    value = (value or "").strip().lower()
    if value in ["si", "sí", "s", "yes", "y"]:
        return "yes"
    if value in ["no", "n"]:
        return "no"
    if value in ["editar", "edit", "e"]:
        return "edit"
    if value in ["feedback", "f"]:
        return "feedback"
    return value


def _build_initial_state(
    user_query: str,
    user_id: str,
    *,
    conversation_id: Optional[str] = None,
    interactive: bool = True,
    auto_approve_sql: bool = False,
    auto_approve_response: bool = False,
    sql_override: Optional[str] = None,
    sql_rejected: bool = False,
    human_feedback: Optional[str] = None,
    response_rejected: bool = False,
) -> Dict[str, Any]:
    conversation_id = conversation_id or str(uuid.uuid4())
    ltm_context = ltm.retrieve_relevant_memories(user_id, user_query)

    return {
        "messages": [{"role": "user", "content": user_query}],
        "user_id": user_id,
        "conversation_id": conversation_id,
        "user_query": user_query,
        "query_intent": None,
        "requires_sql": False,
        "generated_sql": None,
        "sql_approved": False,
        "sql_results": None,
        "sql_override": sql_override,
        "sql_rejected": sql_rejected,
        "draft_response": None,
        "response_approved": False,
        "response_rejected": response_rejected,
        "final_response": None,
        "ltm_context": ltm_context,
        "interactive": interactive,
        "auto_approve_sql": auto_approve_sql,
        "auto_approve_response": auto_approve_response,
        "human_feedback": human_feedback,
        "next_agent": None,
        "status": "running",
        "pending_approval": None,
        "iteration_count": 0,
    }


def _invoke_graph(state: Dict[str, Any]) -> Dict[str, Any]:
    redis_manager.publish_event(
        "langgraph_events",
        {
            "type": "conversation_started",
            "conversation_id": state["conversation_id"],
            "user_id": state["user_id"],
        },
    )
    config = {"configurable": {"thread_id": state["conversation_id"]}}
    return dict(workflow_app.invoke(state, config=config))


def run_conversation(
    user_query: str,
    user_id: str = "usuario_demo",
    *,
    interactive: bool = True,
    auto_approve_sql: bool = False,
    auto_approve_response: bool = False,
    sql_override: Optional[str] = None,
    sql_rejected: bool = False,
    human_feedback: Optional[str] = None,
    response_rejected: bool = False,
    conversation_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Ejecuta una conversación usando LangGraph como orquestador real.

    La función se mantiene como fachada para Streamlit/CLI, pero no coordina
    agentes con if/else. Toda la ruta se ejecuta en `workflow_app.invoke()`.
    """
    state = _build_initial_state(
        user_query,
        user_id,
        conversation_id=conversation_id,
        interactive=interactive,
        auto_approve_sql=auto_approve_sql,
        auto_approve_response=auto_approve_response,
        sql_override=sql_override,
        sql_rejected=sql_rejected,
        human_feedback=human_feedback,
        response_rejected=response_rejected,
    )

    try:
        result = _invoke_graph(state)

        if not interactive:
            return result

        # CLI HITL: el bloqueo humano vive fuera del grafo, pero la ejecución
        # de agentes siempre se reinvoca a través del grafo.
        while result.get("pending_approval") == "sql":
            print("\n" + "=" * 70)
            print("REVISIÓN HUMANA - SQL")
            print("=" * 70)
            print(result.get("generated_sql") or "")

            approval = _normalize_yes_no(input("¿Aprobar? (si/no/editar): "))
            if approval == "no":
                return run_conversation(
                    user_query,
                    user_id,
                    interactive=False,
                    sql_rejected=True,
                    conversation_id=result["conversation_id"],
                )
            if approval == "edit":
                sql_override = input("Ingresa SQL corregido: ").strip()
                result = run_conversation(
                    user_query,
                    user_id,
                    interactive=False,
                    auto_approve_sql=True,
                    auto_approve_response=auto_approve_response,
                    sql_override=sql_override,
                    conversation_id=result["conversation_id"],
                )
                break
            if approval == "yes":
                result = run_conversation(
                    user_query,
                    user_id,
                    interactive=False,
                    auto_approve_sql=True,
                    auto_approve_response=auto_approve_response,
                    conversation_id=result["conversation_id"],
                )
                break

        while result.get("pending_approval") == "response":
            print("\n" + "=" * 70)
            print("REVISIÓN HUMANA - RESPUESTA")
            print("=" * 70)
            print(result.get("draft_response") or "")

            approval = _normalize_yes_no(input("¿Aprobar? (si/no/feedback): "))
            if approval == "no":
                return run_conversation(
                    user_query,
                    user_id,
                    interactive=False,
                    auto_approve_sql=True,
                    response_rejected=True,
                    conversation_id=result["conversation_id"],
                )
            if approval == "feedback":
                feedback = input("Feedback: ").strip()
                result = run_conversation(
                    user_query,
                    user_id,
                    interactive=False,
                    auto_approve_sql=True,
                    human_feedback=feedback,
                    conversation_id=result["conversation_id"],
                )
                break
            if approval == "yes":
                result = run_conversation(
                    user_query,
                    user_id,
                    interactive=False,
                    auto_approve_sql=True,
                    auto_approve_response=True,
                    conversation_id=result["conversation_id"],
                )
                break

        return result

    except Exception as e:
        logger.error(str(e), exc_info=True)
        raise


def main():
    print("=" * 70)
    print("Asistente Chinook - LangGraph")
    print("=" * 70)

    user_id = input("User ID [usuario_demo]: ").strip() or "usuario_demo"

    while True:
        user_query = input("\nPregunta (o 'salir'): ").strip()
        if user_query.lower() in {"salir", "exit", "quit"}:
            break

        result = run_conversation(user_query, user_id, interactive=True)
        print("\nRespuesta:")
        print(result.get("final_response") or result.get("draft_response") or "Sin respuesta")


if __name__ == "__main__":
    main()
