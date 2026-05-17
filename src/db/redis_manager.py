"""Redis connection for streaming and worker coordination."""
import redis
from typing import Any, Optional, Dict
import json
from datetime import datetime
from src.config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class RedisManager:
    """Manager for Redis operations."""
    
    def __init__(self):
        """Initialize Redis client."""
        self.connected = False  #  Inicializar primero
        
        try:
            logger.info(" Conectando a Redis...")
            
            # Parse URL para logging (sin mostrar password)
            from urllib.parse import urlparse
            parsed = urlparse(settings.redis_url)
            safe_url = f"{parsed.scheme}://{parsed.hostname}:{parsed.port}"
            logger.info(f"   Host: {safe_url}")
            
            self.client = redis.from_url(
                settings.redis_url,
                decode_responses=True,
                socket_connect_timeout=10,
                socket_keepalive=True,
                health_check_interval=30
            )
            
            # Test connection
            self.client.ping()
            self.connected = True
            logger.info(" Redis conectado exitosamente")
            
        except redis.ConnectionError as e:
            logger.warning(f"  Error de conexión a Redis: {e}")
            logger.warning("   El sistema continuará sin Redis")
            self.client = None
            self.connected = False
            
        except Exception as e:
            logger.warning(f"  Error inesperado conectando a Redis: {e}")
            logger.warning("   El sistema continuará sin Redis")
            self.client = None
            self.connected = False
    
    def is_connected(self) -> bool:
        """Check if Redis is connected.
        
        Returns:
            True if connected, False otherwise
        """
        return self.connected
    
    def publish_event(self, channel: str, event: Dict[str, Any]) -> None:
        """Publish event to Redis channel.
        
        Args:
            channel: Channel name
            event: Event data
        """
        if not self.connected:
            logger.debug(f"  Redis no conectado, saltando publicación a {channel}")
            return
            
        try:
            message = json.dumps(event)
            self.client.publish(channel, message)
            logger.debug(f" Evento publicado en {channel}: {event.get('type', 'unknown')}")
        except Exception as e:
            logger.error(f" Error publicando a Redis: {e}")
    
    def subscribe_to_channel(self, channel: str):
        """Subscribe to Redis channel.
        
        Args:
            channel: Channel name
            
        Returns:
            PubSub object or None
        """
        if not self.connected:
            logger.warning("  Redis no conectado, no se puede suscribir")
            return None
            
        try:
            pubsub = self.client.pubsub()
            pubsub.subscribe(channel)
            logger.info(f" Suscrito al canal {channel}")
            return pubsub
        except Exception as e:
            logger.error(f" Error suscribiéndose al canal: {e}")
            return None
    
    def set_task_status(
        self,
        task_id: str,
        status: str,
        data: Optional[Dict[str, Any]] = None,
        expiry: int = 3600
    ) -> None:
        """Set task status in Redis.
        
        Args:
            task_id: Task identifier
            status: Task status
            data: Optional task data
            expiry: Expiry time in seconds
        """
        if not self.connected:
            logger.debug(f"  Redis no conectado, saltando actualización de estado")
            return
            
        task_data = {
            "status": status,
            "data": data or {},
            "updated_at": datetime.utcnow().isoformat()
        }
        
        try:
            self.client.setex(
                f"task:{task_id}",
                expiry,
                json.dumps(task_data)
            )
            logger.debug(f" Estado guardado - Task {task_id}: {status}")
        except Exception as e:
            logger.error(f" Error guardando estado de tarea: {e}")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task status from Redis.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task data or None
        """
        if not self.connected:
            return None
            
        try:
            data = self.client.get(f"task:{task_id}")
            return json.loads(data) if data else None
        except Exception as e:
            logger.error(f" Error obteniendo estado de tarea: {e}")
            return None
    
    def cancel_task(self, task_id: str) -> None:
        """Mark task as cancelled.
        
        Args:
            task_id: Task identifier
        """
        if not self.connected:
            logger.warning("  Redis no conectado, no se puede cancelar tarea")
            return
            
        try:
            self.set_task_status(task_id, "cancelled")
            self.publish_event("task_events", {
                "task_id": task_id,
                "event": "cancelled",
                "timestamp": datetime.utcnow().isoformat()
            })
            logger.info(f" Tarea {task_id} cancelada")
        except Exception as e:
            logger.error(f" Error cancelando tarea: {e}")


# Global instance
redis_manager = RedisManager()