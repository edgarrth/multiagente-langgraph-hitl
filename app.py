"""
Interfaz Streamlit con HITL visual completo.
"""

import sys
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.main import run_conversation
from src.db.redis_manager import redis_manager

st.set_page_config(
    page_title="Asistente Chinook",
    page_icon="🎵",
    layout="wide",
)

EXAMPLES = [
    "¿Cuáles son los 5 álbumes más vendidos?",
    "¿Qué artista tiene más canciones?",
    "Lista los clientes de Brasil",
]


def init_session_state():

    defaults = {
        "messages": [],
        "pending_state": None,
        "user_id": "demo",
        "auto_approve_sql": True,
        "auto_approve_response": True,
        "show_sql": True,
        "show_results": True,
    }

    for key, value in defaults.items():

        if key not in st.session_state:
            st.session_state[key] = value


init_session_state()


def render_state_details(state: Dict[str, Any]):

    if not state:
        return

    generated_sql = state.get("generated_sql")

    sql_results: List[Dict[str, Any]] = (
        state.get("sql_results") or []
    )

    with st.expander("Detalles técnicos"):

        st.write(
            "Intent:",
            state.get("query_intent")
        )

        st.write(
            "SQL aprobado:",
            state.get("sql_approved")
        )

        if generated_sql and st.session_state.show_sql:

            st.markdown("### SQL generado")

            st.code(
                generated_sql,
                language="sql"
            )

        if sql_results and st.session_state.show_results:

            st.markdown("### Resultados")

            st.dataframe(
                pd.DataFrame(sql_results),
                use_container_width=True,
            )


def process_prompt(prompt: str):

    result = run_conversation(
        prompt,
        st.session_state.user_id,
        interactive=False,
        auto_approve_sql=(
            st.session_state.auto_approve_sql
        ),
        auto_approve_response=(
            st.session_state
            .auto_approve_response
        ),
    )

    response = (
        result.get("final_response")
        or result.get("draft_response")
        or "Sin respuesta"
    )

    st.session_state.messages.append({
        "role": "user",
        "content": prompt,
    })

    st.session_state.messages.append({
        "role": "assistant",
        "content": response,
        "state": result,
    })

    st.session_state.pending_state = result


with st.sidebar:

    st.title("Configuración")

    st.text_input(
        "User ID",
        key="user_id",
    )

    st.write(
        "Redis:",
        (
            "Conectado"
            if redis_manager.connected
            else "Desconectado"
        ),
    )

    st.toggle(
        "Auto-aprobar SQL",
        key="auto_approve_sql",
    )

    st.toggle(
        "Auto-aprobar respuesta",
        key="auto_approve_response",
    )

    st.toggle(
        "Mostrar SQL",
        key="show_sql",
    )

    st.toggle(
        "Mostrar resultados",
        key="show_results",
    )

    st.markdown("---")

    for example in EXAMPLES:

        if st.button(
            example,
            use_container_width=True,
        ):

            process_prompt(example)

st.title("Asistente Chinook HITL")

if not st.session_state.messages:

    st.info(
        "Haz una pregunta sobre Chinook"
    )

for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        st.markdown(message["content"])

        if (
            message["role"] == "assistant"
            and message.get("state")
        ):

            render_state_details(
                message["state"]
            )

if prompt := st.chat_input(
    "Pregunta sobre Chinook..."
):

    process_prompt(prompt)

    st.rerun()

# =========================================================
# HITL APPROVALS
# =========================================================

pending = st.session_state.get(
    "pending_state"
)

if pending:

    # =====================================================
    # SQL APPROVAL
    # =====================================================

    if (
        pending.get("generated_sql")
        and not pending.get("sql_approved")
    ):

        st.warning(
            "SQL pendiente de aprobación"
        )

        edited_sql = st.text_area(
            "Editar SQL",
            value=pending["generated_sql"],
            height=250,
        )

        feedback_sql = st.text_area(
            "Feedback SQL",
            placeholder="Comentarios opcionales...",
        )

        col1, col2 = st.columns(2)

        with col1:

            if st.button("Aprobar SQL"):

                approved_result = run_conversation(
                    pending["user_query"],
                    st.session_state.user_id,
                    interactive=False,
                    auto_approve_sql=True,
                    auto_approve_response=(
                        st.session_state
                        .auto_approve_response
                    ),
                    sql_override=edited_sql,
                    human_feedback=feedback_sql,
                )

                st.session_state.pending_state = (
                    approved_result
                )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": approved_result.get(
                        "final_response",
                        "SQL aprobado"
                    ),
                    "state": approved_result,
                })

                st.rerun()

        with col2:

            if st.button("Rechazar SQL"):

                st.error("SQL rechazado")

                st.session_state.pending_state = None

                st.rerun()

    # =====================================================
    # RESPONSE APPROVAL
    # =====================================================

    elif (
        pending.get("draft_response")
        and not pending.get("response_approved")
    ):

        st.warning(
            "Respuesta pendiente de aprobación"
        )

        st.markdown(
            pending["draft_response"]
        )

        feedback = st.text_area(
            "Feedback respuesta",
            placeholder="Comentarios opcionales...",
        )

        col1, col2 = st.columns(2)

        with col1:

            if st.button(
                "Aprobar respuesta"
            ):

                approved_result = run_conversation(
                    pending["user_query"],
                    st.session_state.user_id,
                    interactive=False,
                    auto_approve_sql=True,
                    auto_approve_response=True,
                    human_feedback=feedback,
                )

                st.session_state.pending_state = (
                    approved_result
                )

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": approved_result.get(
                        "final_response",
                        "Respuesta aprobada"
                    ),
                    "state": approved_result,
                })

                st.rerun()

        with col2:

            if st.button(
                "Rechazar respuesta"
            ):

                st.error(
                    "Respuesta rechazada"
                )

                st.session_state.pending_state = None

                st.rerun()
