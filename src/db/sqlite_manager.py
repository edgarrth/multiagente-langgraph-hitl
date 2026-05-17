"""Conexión y ejecución de consultas SQLite para la base de datos Chinook."""
import sqlite3
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
from src.config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class SQLiteManager:
    """Gestor para operaciones de base de datos SQLite Chinook."""
    
    def __init__(self, db_path: Optional[str] = None):
        """Inicializa el gestor SQLite.
        
        Args:
            db_path: Ruta al archivo de base de datos SQLite
        """
        self.db_path = db_path or settings.sqlite_db_path
        logger.info(f"Gestor SQLite inicializado con ruta: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Gestor de contexto para conexiones de base de datos."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Error en la base de datos: {e}")
            raise
        finally:
            conn.close()
    
    def execute_query(
        self, 
        query: str, 
        params: Optional[tuple] = None
    ) -> List[Dict[str, Any]]:
        """Ejecuta una consulta SELECT y devuelve los resultados.
        
        Args:
            query: Cadena de consulta SQL
            params: Parámetros opcionales de consulta
            
        Returns:
            Lista de diccionarios con los resultados de la consulta
        """
        logger.info(f"Ejecutando consulta: {query[:100]}...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            
            columns = [desc[0] for desc in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            logger.info(f"La consulta devolvió {len(results)} filas")
            return results
    
    def get_schema(self) -> Dict[str, List[Dict[str, str]]]:
        """Obtiene información del esquema de la base de datos.
        
        Returns:
            Diccionario que mapea nombres de tablas a sus columnas
        """
        schema = {}
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Obtiene todas las tablas
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "ORDER BY name"
            )
            tables = [row[0] for row in cursor.fetchall()]
            
            # Obtiene columnas para cada tabla
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table})")
                columns = [
                    {
                        "name": row[1],
                        "type": row[2],
                        "nullable": not row[3],
                        "primary_key": bool(row[5])
                    }
                    for row in cursor.fetchall()
                ]
                schema[table] = columns
        
        logger.info(f"Esquema obtenido para {len(schema)} tablas")
        return schema
    
    def validate_query(self, query: str) -> bool:
        """Valida la consulta SQL (verificación básica de seguridad).
        
        Args:
            query: Consulta SQL a validar
            
        Returns:
            Verdadero si la consulta parece segura
        """
        query_upper = query.upper().strip()
        
        # Solo permite consultas SELECT
        if not query_upper.startswith("SELECT"):
            logger.warning("La consulta no es una declaración SELECT")
            return False
        
        # Desautoriza operaciones peligrosas
        dangerous_keywords = ["DROP", "DELETE", "INSERT", "UPDATE", "ALTER", "CREATE"]
        if any(keyword in query_upper for keyword in dangerous_keywords):
            logger.warning(f"La consulta contiene una palabra clave peligrosa")
            return False
        
        return True


# Instancia global
sqlite_manager = SQLiteManager()