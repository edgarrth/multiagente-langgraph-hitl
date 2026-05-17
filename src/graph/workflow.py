"""LangGraph workflow definition."""
from typing import Literal
from langgraph.graph import StateGraph, END
from src.graph.state import AgentState
from src.agents.query_interpreter import query_interpreter
from src.agents.sql_expert import sql_expert
from src.agents.explainer import explainer
from src.agents.supervisor import supervisor
from src.config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


def create_workflow() -> StateGraph:
    """Create the multiagent workflow graph.
    
    Returns:
        Compiled StateGraph
    """
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("query_interpreter", query_interpreter.analyze_query)
    workflow.add_node("supervisor", supervisor.route_request)
    workflow.add_node("sql_expert", sql_expert.generate_sql)
    workflow.add_node("sql_executor", sql_expert.execute_sql)
    workflow.add_node("explainer", explainer.explain_results)
    workflow.add_node("finalizer", supervisor.finalize_response)
    
    # Set entry point
    workflow.set_entry_point("query_interpreter")
    
    # Edges
    workflow.add_edge("query_interpreter", "supervisor")
    
    # Conditional from supervisor
    def route_from_supervisor(state: AgentState) -> Literal["sql_expert", "explainer"]:
        if state.get("requires_sql", False):
            return "sql_expert"
        return "explainer"
    
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {"sql_expert": "sql_expert", "explainer": "explainer"}
    )
    
    # SQL path
    workflow.add_edge("sql_expert", "sql_executor")
    workflow.add_edge("sql_executor", "explainer")
    
    # Explainer to finalizer
    workflow.add_edge("explainer", "finalizer")
    workflow.add_edge("finalizer", END)
    
    # Checkpointer
    try:
        from langgraph.checkpoint.postgres import PostgresSaver
        checkpointer = PostgresSaver.from_conn_string(settings.supabase_db_url)
        checkpointer.setup()
        logger.info(" PostgresSaver inicializado")
    except ImportError:
        try:
            from langgraph_checkpoint_postgres import PostgresSaver
            checkpointer = PostgresSaver.from_conn_string(settings.supabase_db_url)
            checkpointer.setup()
            logger.info(" PostgresSaver inicializado")
        except ImportError:
            from langgraph.checkpoint.memory import MemorySaver
            checkpointer = MemorySaver()
            logger.warning("  Usando MemorySaver (solo en memoria)")
    
    app = workflow.compile(checkpointer=checkpointer)
    logger.info(" Grafo compilado")
    return app


workflow_app = create_workflow()