import asyncio
import json
import re
from datetime import datetime, timezone
from enum import Enum, StrEnum
from typing import Any, Mapping
from uuid import UUID, uuid4

from botocore.exceptions import (
    BotoCoreError,
    ClientError,
)
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from src.common.aws_session import get_aws_session
from src.common.config import settings
from src.common.logging_config import logger
from src.models import Article
from src.storage.exceptions import (
    S3BucketNotConfiguredError,
    S3StorageError,
)


SAFE_KEY_COMPONENT_PATTERN = re.compile(
    r"[^a-z0-9._-]+"
)

RESERVED_PARTITION_NAMES = {
    "provider",
    "category",
    "year",
    "month",
    "day",
    "hour",
}


class S3StorageLayer(StrEnum):
    """Supported World News AI S3 storage layers."""

    RAW = "raw"
    PROCESSED = "processed"
    REJECTED = "rejected"
    CURATED = "curated"
    SOCIAL_CARDS = "social-cards"


class S3ObjectLocation(BaseModel):
    """Location and response information for an S3 object."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        frozen=True,
    )

    bucket: str = Field(min_length=3)
    key: str = Field(min_length=1)
    uri: str = Field(min_length=6)
    etag: str | None = None
    version_id: str | None = None


def current_utc_time() -> datetime:
    """Return the current timezone-aware UTC time."""

    return datetime.now(timezone.utc)


def normalize_utc_datetime(
    value: datetime,
) -> datetime:
    """Normalize a datetime value to timezone-aware UTC."""

    if value.tzinfo is None or value.utcoffset() is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def slugify_key_component(value: object) -> str:
    """Convert a value into a safe S3 key component."""

    normalized_value = str(value).strip().casefold()

    normalized_value = SAFE_KEY_COMPONENT_PATTERN.sub(
        "-",
        normalized_value,
    )

    normalized_value = normalized_value.strip(
        "-._"
    )

    return normalized_value or "unknown"


def json_default(value: object) -> object:
    """Convert supported Python objects into JSON values."""

    if isinstance(value, datetime):
        return normalize_utc_datetime(
            value
        ).isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Enum):
        return value.value

    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")

    raise TypeError(
        f"Object of type {type(value).__name__} "
        "is not JSON serializable."
    )


def serialize_json(
    payload: object,
) -> bytes:
    """Serialize a Python object into compact UTF-8 JSON bytes."""

    return json.dumps(
        payload,
        default=json_default,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


class S3NewsStorageService:
    """Store World News AI data in Amazon S3."""

    def __init__(
        self,
        s3_client: Any | None = None,
        bucket_name: str | None = None,
    ) -> None:
        resolved_bucket_name = (
            bucket_name
            if bucket_name is not None
            else settings.aws_s3_data_bucket
        )

        self._bucket_name = (
            resolved_bucket_name.strip()
        )

        if not self._bucket_name:
            raise S3BucketNotConfiguredError()

        self._s3_client = (
            s3_client
            if s3_client is not None
            else get_aws_session().client("s3")
        )

    @property
    def bucket_name(self) -> str:
        """Return the configured S3 bucket name."""

        return self._bucket_name

    @staticmethod
    def _prefix_for_layer(
        layer: S3StorageLayer,
    ) -> str:
        """Return the configured prefix for a storage layer."""

        prefix_mapping = {
            S3StorageLayer.RAW: (
                settings.aws_s3_raw_prefix
            ),
            S3StorageLayer.PROCESSED: (
                settings.aws_s3_processed_prefix
            ),
            S3StorageLayer.REJECTED: (
                settings.aws_s3_rejected_prefix
            ),
            S3StorageLayer.CURATED: (
                settings.aws_s3_curated_prefix
            ),
            S3StorageLayer.SOCIAL_CARDS: (
                settings.aws_s3_social_cards_prefix
            ),
        }

        return prefix_mapping[layer]

    def build_object_key(
        self,
        layer: S3StorageLayer,
        timestamp: datetime,
        identifier: str,
        provider: str | None = None,
        category: str | None = None,
        extra_partitions: Mapping[
            str,
            object,
        ]
        | None = None,
    ) -> str:
        """Create a partition-friendly S3 object key."""

        utc_timestamp = normalize_utc_datetime(
            timestamp
        )

        key_parts = [
            self._prefix_for_layer(layer),
        ]

        if provider:
            key_parts.append(
                "provider="
                f"{slugify_key_component(provider)}"
            )

        if category:
            key_parts.append(
                "category="
                f"{slugify_key_component(category)}"
            )

        if extra_partitions:
            for partition_name in sorted(
                extra_partitions
            ):
                normalized_name = (
                    slugify_key_component(
                        partition_name
                    )
                )

                if (
                    normalized_name
                    in RESERVED_PARTITION_NAMES
                ):
                    raise ValueError(
                        "Reserved S3 partition name: "
                        f"{normalized_name}"
                    )

                normalized_value = (
                    slugify_key_component(
                        extra_partitions[
                            partition_name
                        ]
                    )
                )

                key_parts.append(
                    f"{normalized_name}="
                    f"{normalized_value}"
                )

        key_parts.extend(
            [
                f"year={utc_timestamp:%Y}",
                f"month={utc_timestamp:%m}",
                f"day={utc_timestamp:%d}",
                f"hour={utc_timestamp:%H}",
                (
                    f"{slugify_key_component(identifier)}"
                    ".json"
                ),
            ]
        )

        return "/".join(key_parts)

    async def put_json(
        self,
        key: str,
        payload: object,
    ) -> S3ObjectLocation:
        """Serialize and upload a JSON object to Amazon S3."""

        body = serialize_json(payload)

        try:
            response = await asyncio.to_thread(
                self._s3_client.put_object,
                Bucket=self._bucket_name,
                Key=key,
                Body=body,
                ContentType="application/json",
            )
        except (
            BotoCoreError,
            ClientError,
        ) as exc:
            logger.exception(
                "Amazon S3 put_object failed "
                "bucket=%s key=%s",
                self._bucket_name,
                key,
            )

            raise S3StorageError(
                operation="put_object",
                bucket=self._bucket_name,
                key=key,
                detail=str(exc),
            ) from exc

        raw_etag = response.get("ETag")

        etag = (
            str(raw_etag).strip('"')
            if raw_etag
            else None
        )

        version_id = response.get("VersionId")

        location = S3ObjectLocation(
            bucket=self._bucket_name,
            key=key,
            uri=(
                f"s3://{self._bucket_name}/{key}"
            ),
            etag=etag,
            version_id=(
                str(version_id)
                if version_id
                else None
            ),
        )

        logger.info(
            "JSON object stored in Amazon S3 "
            "bucket=%s key=%s version_id=%s",
            location.bucket,
            location.key,
            location.version_id,
        )

        return location

    async def save_raw_payload(
        self,
        provider: str,
        payload: object,
        source_id: str | None = None,
        query: str | None = None,
        collected_at: datetime | None = None,
        extra_partitions: Mapping[
            str,
            object,
        ]
        | None = None,
    ) -> S3ObjectLocation:
        """Store an unmodified provider response in the raw layer."""

        timestamp = normalize_utc_datetime(
            collected_at or current_utc_time()
        )

        record_id = str(uuid4())

        record = {
            "schema_version": "1.0",
            "record_type": "raw_news_payload",
            "record_id": record_id,
            "provider": provider,
            "source_id": source_id,
            "query": query,
            "collected_at": timestamp.isoformat(),
            "payload": payload,
        }

        key = self.build_object_key(
            layer=S3StorageLayer.RAW,
            timestamp=timestamp,
            identifier=record_id,
            provider=provider,
            extra_partitions=extra_partitions,
        )

        return await self.put_json(
            key=key,
            payload=record,
        )

    async def save_article(
        self,
        article: Article,
        layer: S3StorageLayer = (
            S3StorageLayer.PROCESSED
        ),
        extra_partitions: Mapping[
            str,
            object,
        ]
        | None = None,
    ) -> S3ObjectLocation:
        """Store a validated article in an S3 data layer."""

        if layer not in {
            S3StorageLayer.PROCESSED,
            S3StorageLayer.CURATED,
        }:
            raise ValueError(
                "Articles can only be stored in the "
                "processed or curated layer."
            )

        key = self.build_object_key(
            layer=layer,
            timestamp=article.published_at,
            identifier=str(article.article_id),
            provider=article.source.name,
            category=article.primary_category.value,
            extra_partitions=extra_partitions,
        )

        return await self.put_json(
            key=key,
            payload=article.model_dump(
                mode="json"
            ),
        )

    async def save_rejected_payload(
        self,
        provider: str,
        payload: object,
        reason: str,
        rejected_at: datetime | None = None,
        source_id: str | None = None,
        extra_partitions: Mapping[
            str,
            object,
        ]
        | None = None,
    ) -> S3ObjectLocation:
        """Store rejected data with its rejection reason."""

        cleaned_reason = reason.strip()

        if not cleaned_reason:
            raise ValueError(
                "A rejected payload must include a reason."
            )

        timestamp = normalize_utc_datetime(
            rejected_at or current_utc_time()
        )

        record_id = str(uuid4())

        record = {
            "schema_version": "1.0",
            "record_type": "rejected_news_payload",
            "record_id": record_id,
            "provider": provider,
            "source_id": source_id,
            "reason": cleaned_reason,
            "rejected_at": timestamp.isoformat(),
            "payload": payload,
        }

        key = self.build_object_key(
            layer=S3StorageLayer.REJECTED,
            timestamp=timestamp,
            identifier=record_id,
            provider=provider,
            extra_partitions=extra_partitions,
        )

        return await self.put_json(
            key=key,
            payload=record,
        )