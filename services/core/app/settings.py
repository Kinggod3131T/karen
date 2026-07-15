from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Karen Core"
    app_version: str = "0.3.0"

    karen_workspace: Path = Path.home() / "Workspace"

    ollama_base_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen2.5-coder:3b"

    postgres_user: str = "karen"
    postgres_password: str = "change-this-password"
    postgres_db: str = "karen"
    postgres_port: int = 5432

    redis_port: int = 6379
    qdrant_port: int = 6333

    openrouter_api_key: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
