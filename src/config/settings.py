"""Gestión de configuración usando pydantic-settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Configuración de la aplicación cargada desde variables de entorno."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="allow"
    )
    
    # LangSmith
    langsmith_api_key: str
    langsmith_project: str = "chinook-multiagent"
    langchain_tracing_v2: bool = True
    langchain_endpoint: str = "https://api.smith.langchain.com"
    
    # OpenAI
    openai_api_key: str
    
    # SQLite
    sqlite_db_path: str = "./data/Chinook.sqlite"
    
    # Supabase
    supabase_url: str
    supabase_service_role_key: str
    supabase_db_url: str
    
    # Redis
    redis_url: str
    
    # App
    log_level: str = "INFO"
    environment: str = "development"


# Instancia global de configuración
settings = Settings()