"""Gestión de configuración usando pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow",
    )

    # OpenAI
    openai_api_key: str

    # LangSmith opcional
    langsmith_api_key: Optional[str] = None
    langsmith_project: str = "chinook-multiagent"
    langchain_tracing_v2: bool = False
    langchain_endpoint: str = "https://api.smith.langchain.com"

    # SQLite de dominio Chinook
    sqlite_db_path: str = "./data/Chinook.sqlite"

    # SQLite local para memoria, conversaciones y checkpoints
    local_app_db_path: str = "./data/app_memory.sqlite"
    langgraph_checkpoint_db_path: str = "./data/langgraph_checkpoints.sqlite"

    # Redis local opcional para eventos/estado efímero
    redis_url: str = "redis://localhost:6379/0"

    # App
    log_level: str = "INFO"
    environment: str = "development"


settings = Settings()
