"""SQLite local para memoria persistente y conversaciones.

Reemplaza Supabase para que la PoC pueda ejecutarse completamente local.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.config.settings import settings
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class LocalMemoryManager:
    """Manager local compatible con la interfaz usada por LongTermMemory."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = Path(db_path or settings.local_app_db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        logger.info("Gestor local SQLite de memoria inicializado: %s", self.db_path)

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self.get_connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    conversation_id TEXT NOT NULL,
                    messages TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT NOT NULL DEFAULT '{}',
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_memories_user_created ON memories(user_id, created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conversations_user_created ON conversations(user_id, created_at DESC)"
            )

    @staticmethod
    def _serialize_messages(messages: List[Any]) -> str:
        serialized = []
        for msg in messages:
            if isinstance(msg, dict):
                serialized.append(msg)
            else:
                serialized.append({
                    "role": getattr(msg, "type", "unknown"),
                    "content": getattr(msg, "content", str(msg)),
                })
        return json.dumps(serialized, ensure_ascii=False)

    def save_conversation(
        self,
        user_id: str,
        conversation_id: str,
        messages: List[Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO conversations(user_id, conversation_id, messages, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    conversation_id,
                    self._serialize_messages(messages),
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now,
                ),
            )
            row_id = cur.lastrowid
        logger.info("Conversación %s guardada en SQLite local", conversation_id)
        return {"id": row_id, "user_id": user_id, "conversation_id": conversation_id, "created_at": now}

    def save_memory(
        self,
        user_id: str,
        memory_type: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            cur = conn.execute(
                """
                INSERT INTO memories(user_id, memory_type, content, metadata, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    memory_type,
                    content,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now,
                ),
            )
            row_id = cur.lastrowid
        logger.info("Memoria guardada en SQLite local - tipo: %s", memory_type)
        return {"id": row_id, "user_id": user_id, "memory_type": memory_type, "content": content, "created_at": now}

    def get_user_memories(
        self,
        user_id: str,
        memory_type: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        sql = "SELECT * FROM memories WHERE user_id = ?"
        params: List[Any] = [user_id]
        if memory_type:
            sql += " AND memory_type = ?"
            params.append(memory_type)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        with self.get_connection() as conn:
            rows = conn.execute(sql, params).fetchall()
        return [dict(row) for row in rows]

    def get_conversation_history(self, user_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM conversations
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]


local_memory_manager = LocalMemoryManager()
