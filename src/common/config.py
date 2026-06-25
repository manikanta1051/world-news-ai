from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Central configuration for the World News AI application."""

    # Application
    app_name: str = "World News AI"
    app_env: Literal[
        "development",
        "testing",
        "production",
    ] = "development"
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

    # HTTP client
    http_timeout_seconds: float = Field(
        default=20.0,
        gt=0,
        le=120,
    )
    http_max_connections: int = Field(
        default=20,
        ge=1,
        le=200,
    )
    http_max_keepalive_connections: int = Field(
        default=10,
        ge=0,
        le=100,
    )
    http_retry_attempts: int = Field(
        default=3,
        ge=1,
        le=5,
    )
    http_retry_min_wait_seconds: float = Field(
        default=1.0,
        ge=0,
        le=30,
    )
    http_retry_max_wait_seconds: float = Field(
        default=5.0,
        ge=0,
        le=60,
    )
    http_user_agent: str = Field(
        default="World-News-AI/0.1",
        min_length=3,
        max_length=200,
    )

    # News sources
    gdelt_base_url: str = (
        "https://api.gdeltproject.org/api/v2/doc/doc"
    )
    news_api_key: str = ""

    # AI service
    groq_api_key: str = ""

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = Field(
        default=5432,
        ge=1,
        le=65535,
    )
    postgres_db: str = "world_news"
    postgres_user: str = "world_news_user"
    postgres_password: str = ""

    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_news_topic: str = "raw-news-articles"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = Field(
        default=6379,
        ge=1,
        le=65535,
    )

    # Elasticsearch
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "news-articles"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @model_validator(mode="after")
    def validate_http_configuration(self) -> Self:
        """Validate relationships between HTTP settings."""

        if (
            self.http_max_keepalive_connections
            > self.http_max_connections
        ):
            raise ValueError(
                "HTTP_MAX_KEEPALIVE_CONNECTIONS cannot be "
                "greater than HTTP_MAX_CONNECTIONS."
            )

        if (
            self.http_retry_min_wait_seconds
            > self.http_retry_max_wait_seconds
        ):
            raise ValueError(
                "HTTP_RETRY_MIN_WAIT_SECONDS cannot be "
                "greater than HTTP_RETRY_MAX_WAIT_SECONDS."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    """Return one shared settings object."""

    return Settings()


settings = get_settings()