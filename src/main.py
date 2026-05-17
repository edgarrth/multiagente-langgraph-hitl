"""Main entry point for the multiagent system."""

import uuid
from typing import Dict, Any, Optional

from src.agents.query_interpreter import query_interpreter
from src.agents.supervisor import supervisor
from src.agents.sql_expert import sql_expert
from src.agents.explainer import explainer
from src.memory.long_term import ltm
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


def run_conversation(
    user_query: str,
    user_id: str = "usuario_demo",
    *,
    interactive: bool = True,
    auto_approve_sql: bool = False,
    auto_approve_response: bool = False,
    sql_override: Optional[str] = None,
    human_feedback: Optional[str] = None,
) -> Dict[str, Any]:

    conversation_id = str(uuid.uuid4())

    ltm_context = ltm.retrieve_relevant_memories(
        user_id,
        user_query
    )

    state = {
        "messages": [{"role": "user", "content": user_query}],
        "user_id": user_id,
        "conversation_id": conversation_id,
        "user_query": user_query,
        "query_intent": None,
        "requires_sql": False,
        "generated_sql": None,
        "sql_approved": False,
        "sql_results": None,
        "draft_response": None,
        "response_approved": False,
        "final_response": None,
        "ltm_context": ltm_context,
        "next_agent": None,
        "human_feedback": human_feedback,
        "iteration_count": 0,
    }

    try:

        state = query_interpreter.analyze_query(state)
        state = supervisor.route_request(state)

        # ======================================================
        # SQL
        # ======================================================

        if state.get("requires_sql", False):

            state = sql_expert.generate_sql(state)

            if sql_override:
                state["generated_sql"] = sql_override
                state["sql_approved"] = True

            if (
                state.get("generated_sql")
                and not state.get("sql_approved", False)
            ):

                # AUTO APPROVE
                if auto_approve_sql:

                    state["sql_approved"] = True

                # CLI
                elif interactive:

                    print("\n" + "=" * 70)
                    print("REVISIÓN HUMANA - SQL")
                    print("=" * 70)

                    print(state["generated_sql"])

                    while True:

                        approval = _normalize_yes_no(
                            input(
                                "¿Aprobar? "
                                "(si/no/editar): "
                            )
                        )

                        if approval == "yes":

                            state["sql_approved"] = True
                            break

                        if approval == "edit":

                            new_sql = input(
                                "Ingresa SQL corregido: "
                            ).strip()

                            if new_sql:

                                state["generated_sql"] = (
                                    new_sql
                                )

                                state["sql_approved"] = True
                                break

                            continue

                        if approval == "no":

                            state["final_response"] = (
                                "Consulta SQL rechazada."
                            )

                            return state

                # STREAMLIT/API
                else:

                    state["final_response"] = (
                        "SQL pendiente aprobación."
                    )

                    return state

            # EXECUTE SQL
            if state.get("sql_approved", False):

                state = sql_expert.execute_sql(state)

        # ======================================================
        # EXPLAINER
        # ======================================================

        state = explainer.explain_results(state)

        # ======================================================
        # RESPONSE APPROVAL
        # ======================================================

        if state.get("draft_response"):

            if human_feedback:

                state["human_feedback"] = (
                    human_feedback
                )

                state["response_approved"] = True

            elif auto_approve_response:

                state["response_approved"] = True

            # CLI
            elif interactive:

                print("\n" + "=" * 70)
                print("REVISIÓN HUMANA - RESPUESTA")
                print("=" * 70)

                print(state["draft_response"])

                while True:

                    approval = _normalize_yes_no(
                        input(
                            "¿Aprobar? "
                            "(si/no/feedback): "
                        )
                    )

                    if approval == "yes":

                        state["response_approved"] = True
                        break

                    if approval == "feedback":

                        feedback = input(
                            "Feedback: "
                        ).strip()

                        if feedback:

                            state["human_feedback"] = (
                                feedback
                            )

                            state["response_approved"] = True
                            break

                    if approval == "no":

                        state["final_response"] = (
                            "Respuesta rechazada."
                        )

                        return state

            # STREAMLIT/API
            else:

                state["final_response"] = (
                    state["draft_response"]
                )

                return state

        # ======================================================
        # FINALIZER
        # ======================================================

        state = supervisor.finalize_response(state)

        return state

    except Exception as e:

        logger.error(str(e), exc_info=True)

        raise


def main():

    print("=" * 70)
    print("Asistente Chinook")
    print("=" * 70)

    user_id = input(
        "ID usuario (Enter='demo'): "
    ).strip() or "demo"

    while True:

        query = input(
            "\nPregunta: "
        ).strip()

        if query.lower() in [
            "exit",
            "salir"
        ]:
            break

        if not query:
            continue

        result = run_conversation(
            query,
            user_id,
            interactive=True,
        )

        print("\n" + "=" * 70)
        print(result.get("final_response"))
        print("=" * 70)


if __name__ == "__main__":
    main()
