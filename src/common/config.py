from functools import lru_cache
from pathlib import Path
from typing import Literal, Self

from pydantic import (
    Field,
    SecretStr,
    field_validator,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


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

    # AWS
    aws_region: str = Field(
        default="us-east-1",
        pattern=r"^[a-z]{2}(?:-gov)?-[a-z0-9-]+-\d$",
    )
    aws_profile: str | None = "world-news-dev"

    # Amazon S3 data lake
    aws_s3_data_bucket: str = ""
    aws_s3_raw_prefix: str = "raw/news"
    aws_s3_processed_prefix: str = "processed/news"
    aws_s3_rejected_prefix: str = "rejected/news"
    aws_s3_curated_prefix: str = "curated/news"
    aws_s3_social_cards_prefix: str = "social-cards"

    # Amazon RDS PostgreSQL
    aws_rds_secret_id: str = ""

    postgres_host: str = ""
    postgres_port: int = Field(
        default=5432,
        ge=1,
        le=65535,
    )
    postgres_db: str = "world_news"
    postgres_user: str = ""
    postgres_password: SecretStr = SecretStr("")

    postgres_ssl_mode: Literal[
        "disable",
        "allow",
        "prefer",
        "require",
        "verify-ca",
        "verify-full",
    ] = "require"

    postgres_echo: bool = False
    postgres_pool_size: int = Field(
        default=5,
        ge=1,
        le=50,
    )
    postgres_max_overflow: int = Field(
        default=10,
        ge=0,
        le=100,
    )

    # Kafka or future Amazon MSK
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_news_topic: str = "raw-news-articles"

    # Redis or future Amazon ElastiCache
    redis_host: str = "localhost"
    redis_port: int = Field(
        default=6379,
        ge=1,
        le=65535,
    )

    # Elasticsearch or future Amazon OpenSearch
    elasticsearch_url: str = "http://localhost:9200"
    elasticsearch_index: str = "news-articles"

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("aws_profile", mode="before")
    @classmethod
    def convert_empty_profile_to_none(
        cls,
        value: object,
    ) -> object:
        """Treat an empty AWS profile as no explicit profile."""

        if isinstance(value, str) and not value.strip():
            return None

        return value

    @field_validator(
        "aws_s3_raw_prefix",
        "aws_s3_processed_prefix",
        "aws_s3_rejected_prefix",
        "aws_s3_curated_prefix",
        "aws_s3_social_cards_prefix",
    )
    @classmethod
    def normalize_s3_prefix(
        cls,
        value: str,
    ) -> str:
        """Store S3 prefixes without leading or trailing slashes."""

        normalized_value = value.strip().strip("/")

        if not normalized_value:
            raise ValueError(
                "An S3 prefix cannot be empty."
            )

        return normalized_value

    @model_validator(mode="after")
    def validate_configuration(self) -> Self:
        """Validate relationships between settings."""

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

        s3_prefixes = [
            self.aws_s3_raw_prefix,
            self.aws_s3_processed_prefix,
            self.aws_s3_rejected_prefix,
            self.aws_s3_curated_prefix,
            self.aws_s3_social_cards_prefix,
        ]

        if len(s3_prefixes) != len(set(s3_prefixes)):
            raise ValueError(
                "Amazon S3 storage prefixes must be unique."
            )

        return self


@lru_cache
def get_settings() -> Settings:
    """Return one shared settings object."""

    return Settings()


settings = get_settings()