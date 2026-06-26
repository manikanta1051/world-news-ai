import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from botocore.exceptions import ClientError

from src.models import Article
from src.storage import (
    S3BucketNotConfiguredError,
    S3NewsStorageService,
    S3StorageError,
    S3StorageLayer,
    serialize_json,
    slugify_key_component,
)


SAMPLE_ARTICLE_FILE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "sample_article.json"
)


class FakeS3Client:
    """Capture S3 uploads without contacting AWS."""

    def __init__(self) -> None:
        self.put_calls: list[dict[str, Any]] = []

    def put_object(
        self,
        **kwargs: Any,
    ) -> dict[str, str]:
        """Record the upload and return a fake S3 response."""

        self.put_calls.append(kwargs)

        return {
            "ETag": '"fake-etag-123"',
            "VersionId": "fake-version-1",
        }


class FailingS3Client:
    """Simulate an Amazon S3 access failure."""

    def put_object(
        self,
        **kwargs: Any,
    ) -> dict[str, str]:
        """Raise a realistic Boto3 client error."""

        raise ClientError(
            error_response={
                "Error": {
                    "Code": "AccessDenied",
                    "Message": "Access denied",
                }
            },
            operation_name="PutObject",
        )


def create_service(
    client: Any | None = None,
) -> S3NewsStorageService:
    """Create a service with a fixed test bucket."""

    return S3NewsStorageService(
        s3_client=client or FakeS3Client(),
        bucket_name="world-news-ai-test-bucket",
    )


def load_sample_article() -> Article:
    """Load the existing sample Article fixture."""

    payload = json.loads(
        SAMPLE_ARTICLE_FILE.read_text(
            encoding="utf-8"
        )
    )

    return Article.model_validate(payload)


def test_slugify_key_component() -> None:
    """Confirm that S3 key values are normalized."""

    assert (
        slugify_key_component(
            "Politics & Diplomacy"
        )
        == "politics-diplomacy"
    )

    assert (
        slugify_key_component(
            " Telangana News "
        )
        == "telangana-news"
    )


def test_serialize_json_returns_utf8_bytes() -> None:
    """Confirm that JSON serialization supports Unicode."""

    result = serialize_json(
        {
            "headline": "भारत समाचार",
            "published_at": datetime(
                2026,
                6,
                26,
                12,
                0,
                tzinfo=timezone.utc,
            ),
        }
    )

    assert isinstance(result, bytes)

    decoded_result = json.loads(
        result.decode("utf-8")
    )

    assert (
        decoded_result["headline"]
        == "भारत समाचार"
    )
    assert decoded_result[
        "published_at"
    ].startswith("2026-06-26T12:00:00")


def test_build_raw_object_key() -> None:
    """Confirm that raw keys include provider and date partitions."""

    service = create_service()

    key = service.build_object_key(
        layer=S3StorageLayer.RAW,
        timestamp=datetime(
            2026,
            6,
            26,
            18,
            30,
            tzinfo=timezone.utc,
        ),
        identifier="Record 123",
        provider="GDELT",
    )

    assert key == (
        "raw/news/"
        "provider=gdelt/"
        "year=2026/"
        "month=06/"
        "day=26/"
        "hour=18/"
        "record-123.json"
    )


def test_save_raw_payload_uploads_json() -> None:
    """Confirm that a raw provider response is uploaded."""

    fake_client = FakeS3Client()
    service = create_service(fake_client)

    location = asyncio.run(
        service.save_raw_payload(
            provider="GDELT",
            source_id="gdelt-doc-api",
            query="renewable energy",
            collected_at=datetime(
                2026,
                6,
                26,
                18,
                30,
                tzinfo=timezone.utc,
            ),
            payload={
                "articles": [
                    {
                        "title": "Example article",
                    }
                ]
            },
        )
    )

    assert len(fake_client.put_calls) == 1

    upload = fake_client.put_calls[0]

    assert upload["Bucket"] == (
        "world-news-ai-test-bucket"
    )
    assert upload["ContentType"] == (
        "application/json"
    )

    stored_record = json.loads(
        upload["Body"].decode("utf-8")
    )

    assert stored_record["provider"] == "GDELT"
    assert stored_record["source_id"] == (
        "gdelt-doc-api"
    )
    assert stored_record["query"] == (
        "renewable energy"
    )
    assert stored_record["record_type"] == (
        "raw_news_payload"
    )
    assert "articles" in stored_record["payload"]

    assert location.etag == "fake-etag-123"
    assert location.version_id == (
        "fake-version-1"
    )
    assert location.uri.startswith(
        "s3://world-news-ai-test-bucket/"
    )


def test_save_article_supports_india_partitions() -> None:
    """Confirm that processed articles support state partitions."""

    fake_client = FakeS3Client()
    service = create_service(fake_client)

    article = load_sample_article()

    location = asyncio.run(
        service.save_article(
            article,
            extra_partitions={
                "country": "IN",
                "state": "TG",
            },
        )
    )

    assert (
        "processed/news/"
        in location.key
    )
    assert "provider=example-news/" in location.key
    assert "category=energy/" in location.key
    assert "country=in/" in location.key
    assert "state=tg/" in location.key
    assert location.key.endswith(
        f"{article.article_id}.json"
    )

    upload = fake_client.put_calls[0]

    stored_article = json.loads(
        upload["Body"].decode("utf-8")
    )

    assert stored_article["title"] == article.title
    assert stored_article["article_id"] == str(
        article.article_id
    )


def test_save_rejected_payload_records_reason() -> None:
    """Confirm rejected data stores its failure reason."""

    fake_client = FakeS3Client()
    service = create_service(fake_client)

    location = asyncio.run(
        service.save_rejected_payload(
            provider="RSS",
            source_id="example-feed",
            reason="Article URL was missing",
            rejected_at=datetime(
                2026,
                6,
                26,
                19,
                0,
                tzinfo=timezone.utc,
            ),
            payload={
                "title": "Invalid article",
            },
        )
    )

    assert location.key.startswith(
        "rejected/news/provider=rss/"
    )

    stored_record = json.loads(
        fake_client.put_calls[0][
            "Body"
        ].decode("utf-8")
    )

    assert stored_record["reason"] == (
        "Article URL was missing"
    )
    assert stored_record["record_type"] == (
        "rejected_news_payload"
    )


def test_empty_bucket_name_is_rejected() -> None:
    """Confirm that storage cannot start without a bucket."""

    with pytest.raises(
        S3BucketNotConfiguredError
    ):
        S3NewsStorageService(
            s3_client=FakeS3Client(),
            bucket_name="",
        )


def test_reserved_extra_partition_is_rejected() -> None:
    """Confirm that date partition names cannot be replaced."""

    service = create_service()

    with pytest.raises(
        ValueError,
        match="Reserved S3 partition name",
    ):
        service.build_object_key(
            layer=S3StorageLayer.RAW,
            timestamp=datetime(
                2026,
                6,
                26,
                tzinfo=timezone.utc,
            ),
            identifier="test-record",
            extra_partitions={
                "year": "2020",
            },
        )


def test_s3_client_error_is_converted() -> None:
    """Confirm that Boto3 failures use a project exception."""

    service = create_service(
        FailingS3Client()
    )

    with pytest.raises(
        S3StorageError
    ) as error:
        asyncio.run(
            service.put_json(
                key="raw/news/test.json",
                payload={
                    "status": "test",
                },
            )
        )

    assert error.value.operation == "put_object"
    assert error.value.bucket == (
        "world-news-ai-test-bucket"
    )
    assert error.value.key == (
        "raw/news/test.json"
    )