"""SQL Expert Agent - generates and validates SQL queries."""
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from src.config.settings import settings
from src.db.sqlite_manager import sqlite_manager
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SQLExpertAgent:
    """Agent that generates SQL queries for Chinook database."""
    
    def __init__(self):
        """Initialize SQL expert agent."""
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0,
            api_key=settings.openai_api_key
        )
        self.db = sqlite_manager
        self.schema = self._get_schema_description()
        logger.info("Agente Experto SQL inicializado")
    
    def _get_schema_description(self) -> str:
        """Get a text description of the database schema."""
        schema = self.db.get_schema()
        
        description = "Chinook Database Schema:\n\n"
        for table, columns in schema.items():
            description += f"Table: {table}\n"
            for col in columns:
                pk = " (PRIMARY KEY)" if col['primary_key'] else ""
                description += f"  - {col['name']}: {col['type']}{pk}\n"
            description += "\n"
        
        return description
    
    def generate_sql(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Generate SQL query based on user question.
        
        Args:
            state: Current graph state
            
        Returns:
            Updated state with generated SQL
        """
        user_query = state["user_query"]
        logger.info(f"Generando SQL para: {user_query}")
        
        # Manejo especial para consultas meta (sobre el schema)
        query_lower = user_query.lower()
        if any(keyword in query_lower for keyword in ['tablas', 'tables', 'esquema', 'schema', 'estructura', 'enumere']):
            # Retornar directamente el schema sin SQL
            tables_list = list(self.db.get_schema().keys())
            logger.info(f"Consulta de esquema detectada. Tablas: {tables_list}")
            return {
                **state,
                "generated_sql": None,
                "sql_approved": True,  # Auto-aprobar consultas de schema
                "sql_results": [{"tabla": table} for table in tables_list],
                "next_agent": "explainer"
            }
        
        system_prompt = f"""Eres un experto desarrollador SQL para la base de datos Chinook de una tienda de música.

{self.schema}

Genera una consulta SQL segura y eficiente para responder la pregunta del usuario.

REGLAS IMPORTANTES:
- Usa SOLO declaraciones SELECT
- Incluye cláusulas WHERE y JOINs apropiados cuando sea necesario
- Limita los resultados a números razonables (LIMIT 20 o menos)
- Retorna SOLO la consulta SQL, sin explicaciones
- NO uses comentarios en el SQL
- NO uses markdown ni bloques de código
- Asegúrate de que la consulta sea válida y ejecutable

Si la pregunta NO puede responderse con los datos disponibles, responde exactamente con: NO_SQL_POSIBLE

Ejemplos de buenas consultas:
- Para "álbumes más vendidos": SELECT a.Title, COUNT(*) as Sales FROM Album a JOIN Track t ON a.AlbumId = t.AlbumId JOIN InvoiceLine il ON t.TrackId = il.TrackId GROUP BY a.AlbumId ORDER BY Sales DESC LIMIT 10
- Para "canciones más largas": SELECT Name, Milliseconds FROM Track ORDER BY Milliseconds DESC LIMIT 10
"""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Pregunta: {user_query}")
        ]
        
        response = self.llm.invoke(messages)
        sql = response.content.strip()
        
        # Remove markdown code blocks if present
        if sql.startswith("```sql"):
            sql = sql.split("```sql")[1].split("```")[0].strip()
        elif sql.startswith("```"):
            sql = sql.split("```")[1].split("```")[0].strip()
        
        # Remove comments
        sql_lines = [line for line in sql.split('\n') if not line.strip().startswith('--')]
        sql = '\n'.join(sql_lines).strip()
        
        # Check if it's a valid response
        if sql == "NO_SQL_POSIBLE" or not sql:
            logger.warning("No se pudo generar SQL válido")
            return {
                **state,
                "generated_sql": None,
                "sql_approved": False,
                "sql_results": [],  #  SIEMPRE LISTA, NUNCA None
                "draft_response": "No puedo generar una consulta SQL para esta pregunta con los datos disponibles.",
                "next_agent": "explainer"
            }
        
        logger.info(f"SQL generado: {sql[:100]}...")
        
        return {
            **state,
            "generated_sql": sql,
            "sql_approved": False,  # Requiere aprobación humana
            "next_agent": "hitl_sql_review"
        }
    
    def execute_sql(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Execute approved SQL query.
        
        Args:
            state: Current graph state
            
        Returns:
            Updated state with query results
        """
        sql = state.get("generated_sql")
        
        # Si no hay SQL pero sí hay resultados (caso de schema), pasarlos
        if not sql:
            if state.get("sql_results") is not None:
                logger.info(" Usando resultados pre-cargados (schema)")
                return {
                    **state,
                    "next_agent": "explainer"
                }
            
            logger.warning("SQL no disponible y no hay resultados pre-cargados")
            return {
                **state,
                "sql_results": [],  #  SIEMPRE LISTA
                "draft_response": "No se pudo generar una consulta SQL válida.",
                "next_agent": "explainer"
            }
        
        # Verificar aprobación
        if not state.get("sql_approved", False):
            logger.warning("SQL no aprobado por el usuario")
            return {
                **state,
                "sql_results": [],  #  SIEMPRE LISTA
                "draft_response": "La consulta SQL no fue aprobada.",
                "next_agent": "explainer"
            }
        
        # Validar query
        if not self.db.validate_query(sql):
            logger.error("Validación de SQL falló - query no segura")
            return {
                **state,
                "sql_results": [],  #  SIEMPRE LISTA
                "draft_response": "No puedo ejecutar esta consulta por razones de seguridad.",
                "next_agent": "explainer"
            }
        
        # Ejecutar query
        try:
            results = self.db.execute_query(sql)
            logger.info(f" SQL ejecutado exitosamente - {len(results)} filas retornadas")
            
            if len(results) > 0:
                logger.info(f" Muestra: {results[0]}")
            
            return {
                **state,
                "sql_results": results,  #  SIEMPRE LISTA (execute_query retorna lista)
                "next_agent": "explainer"
            }
            
        except Exception as e:
            logger.error(f" Error ejecutando SQL: {e}")
            return {
                **state,
                "sql_results": [],  #  SIEMPRE LISTA EN CASO DE ERROR
                "draft_response": f"Error al ejecutar la consulta: {str(e)}",
                "next_agent": "explainer"
            }


# Global instance
sql_expert = SQLExpertAgent()