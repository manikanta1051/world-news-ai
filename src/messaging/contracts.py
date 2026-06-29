from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any, Literal, Self
from uuid import UUID, uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


MESSAGE_SCHEMA_VERSION = "1.0"
MAX_QUEUE_RETRY_COUNT = 5


def current_utc_time() -> datetime:
    """Return the current UTC time."""

    return datetime.now(timezone.utc)


class QueueMessageType(StrEnum):
    """Supported Step 10 queue-message types."""

    INGESTION_TRIGGER = "ingestion_trigger"
    ARTICLE_PROCESSING = "article_processing"


class QueueMessageBase(BaseModel):
    """Shared fields and JSON helpers for queue messages."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        validate_assignment=True,
    )

    schema_version: str = Field(
        default=MESSAGE_SCHEMA_VERSION,
        min_length=1,
        max_length=20,
    )
    message_id: UUID = Field(
        default_factory=uuid4,
    )
    created_at: datetime = Field(
        default_factory=current_utc_time,
    )

    def to_json(self) -> str:
        """Serialize the message for EventBridge or SQS."""

        return self.model_dump_json()

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> Self:
        """Deserialize and validate a queue message."""

        return cls.model_validate_json(value)


class ScheduledIngestionMessage(QueueMessageBase):
    """EventBridge-to-Lambda ingestion request."""

    message_type: Literal[
        QueueMessageType.INGESTION_TRIGGER
    ] = QueueMessageType.INGESTION_TRIGGER

    provider: str = Field(
        min_length=1,
        max_length=100,
    )
    query: str = Field(
        min_length=1,
        max_length=1000,
    )
    max_records: int = Field(
        default=25,
        ge=1,
        le=250,
    )
    timespan: str = Field(
        default="24h",
        pattern=(
            r"^[1-9]\d*"
            r"(min|h|hours|d|days|w|weeks|m|months)$"
        ),
    )
    source_id: str | None = Field(
        default=None,
        max_length=200,
    )
    extra_partitions: dict[
        str,
        str | int | float | bool,
    ] = Field(default_factory=dict)

    @field_validator(
        "timespan",
        mode="before",
    )
    @classmethod
    def normalize_timespan(
        cls,
        value: object,
    ) -> object:
        """Normalize timespan before pattern validation."""

        if isinstance(value, str):
            return value.strip().lower()

        return value


class ArticleProcessingMessage(QueueMessageBase):
    """SQS message for processing one validated article."""

    message_type: Literal[
        QueueMessageType.ARTICLE_PROCESSING
    ] = QueueMessageType.ARTICLE_PROCESSING

    provider: str = Field(
        min_length=1,
        max_length=100,
    )
    raw_s3_uri: str = Field(
        min_length=6,
        max_length=2048,
    )
    article_payload: dict[str, Any]
    country_scores: dict[
        str,
        Decimal,
    ] = Field(default_factory=dict)
    state_scores: dict[
        str,
        Decimal,
    ] = Field(default_factory=dict)
    primary_state_code: str | None = Field(
        default=None,
        max_length=20,
    )
    state_detection_method: str | None = Field(
        default=None,
        max_length=100,
    )
    retry_count: int = Field(
        default=0,
        ge=0,
        le=MAX_QUEUE_RETRY_COUNT,
    )

    @field_validator("raw_s3_uri")
    @classmethod
    def validate_raw_s3_uri(
        cls,
        value: str,
    ) -> str:
        """Require an S3 URI containing a bucket and key."""

        normalized_value = value.strip()

        if not normalized_value.startswith("s3://"):
            raise ValueError(
                "raw_s3_uri must start with s3://."
            )

        path_value = normalized_value.removeprefix(
            "s3://"
        )

        bucket, separator, key = path_value.partition(
            "/"
        )

        if (
            not separator
            or not bucket.strip()
            or not key.strip()
        ):
            raise ValueError(
                "raw_s3_uri must include a bucket and key."
            )

        return normalized_value

    @field_validator(
        "country_scores",
        "state_scores",
        mode="before",
    )
    @classmethod
    def normalize_scores(
        cls,
        value: object,
    ) -> object:
        """Normalize codes and validate relevance scores."""

        if value is None:
            return {}

        if not isinstance(value, dict):
            raise ValueError(
                "Relevance scores must be a dictionary."
            )

        normalized_scores: dict[
            str,
            Decimal,
        ] = {}

        for raw_code, raw_score in value.items():
            code = str(raw_code).strip().upper()

            if not code:
                raise ValueError(
                    "A relevance mapping code cannot be empty."
                )

            score = Decimal(str(raw_score))

            if score < 0 or score > 1:
                raise ValueError(
                    "Relevance scores must be between 0 and 1."
                )

            normalized_scores[code] = score

        return normalized_scores

    @field_validator(
        "primary_state_code",
        mode="before",
    )
    @classmethod
    def normalize_primary_state_code(
        cls,
        value: object,
    ) -> object:
        """Normalize the optional primary-state code."""

        if value is None:
            return None

        normalized_value = str(value).strip().upper()

        return normalized_value or None

    @model_validator(mode="after")
    def validate_primary_state_mapping(
        self,
    ) -> "ArticleProcessingMessage":
        """Require the primary state in state_scores."""

        if (
            self.primary_state_code is not None
            and self.primary_state_code
            not in self.state_scores
        ):
            raise ValueError(
                "primary_state_code must exist in state_scores."
            )

        return self