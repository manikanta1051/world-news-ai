from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Central configuration for the World News AI application."""

    # Application
    app_name: str = "World News AI"
    app_env: Literal["development", "testing", "production"] = "development"
    app_debug: bool = True

    # Logging
    log_level: Literal[
        "DEBUG",
        "INFO",
        "WARNING",
        "ERROR",
        "CRITICAL",
    ] = "INFO"
    log_file: str = "logs/world_news_ai.log"

    # News sources
    gdelt_base_url: str = "https://api.gdeltproject.org/api/v2/doc/doc"
    news_api_key: str = ""

    # AI service
    groq_api_key: str = ""

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = Field(default=5432, ge=1, le=65535)
    postgres_db: str = "world_news"
    postgres_user: str = "world_news_user"
    postgres_password: str = ""

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_news_topic: str = "raw-news-articles"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = Field(default=6379, ge=1, le=65535)

    # Elasticsearch
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "news-articles"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    """Return one shared settings object."""

    return Settings()


settings = get_settings()