from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.models import Article
from src.services import (
    ArticleIngestionRequest,
    ArticlePersistenceError,
    ArticlePersistenceResult,
    BatchIngestionCoordinator,
    IngestionPersistenceService,
    PersistenceStatus,
    RawPayloadPersistenceError,
    RejectedIngestionItem,
    RejectedPayloadPersistenceError,
)
from src.storage.s3_service import S3ObjectLocation


def create_coordinator() -> tuple[
    BatchIngestionCoordinator,
    Mock,
]:
    """Create a coordinator with mocked persistence."""

    persistence_service = Mock(
        spec=IngestionPersistenceService
    )

    persistence_service.store_raw_payload = AsyncMock()
    persistence_service.persist_article = AsyncMock()
    persistence_service.store_rejected_payload = AsyncMock()

    coordinator = BatchIngestionCoordinator(
        persistence_service=persistence_service
    )

    return coordinator, persistence_service


def create_article_mock() -> Mock:
    """Create an Article-compatible mock."""

    return Mock(spec=Article)


@pytest.mark.asyncio
async def test_batch_counts_stored_duplicate_and_rejected(
) -> None:
    """Confirm a mixed batch returns correct counts."""

    coordinator, persistence_service = (
        create_coordinator()
    )

    raw_uri = (
        "s3://world-news-test-bucket/"
        "raw/gdelt/provider-response.json"
    )

    persistence_service.store_raw_payload.return_value = (
        S3ObjectLocation(
            bucket="world-news-test-bucket",
            key=(
                "raw/gdelt/"
                "provider-response.json"
            ),
            uri=raw_uri,
        )
    )

    stored_result_one = ArticlePersistenceResult(
        status=PersistenceStatus.STORED,
        article_id=uuid4(),
        raw_s3_uri=raw_uri,
        processed_s3_uri=(
            "s3://world-news-test-bucket/"
            "processed/article-one.json"
        ),
        source_created=True,
    )

    duplicate_result = ArticlePersistenceResult(
        status=PersistenceStatus.DUPLICATE,
        article_id=uuid4(),
        raw_s3_uri=raw_uri,
        processed_s3_uri=(
            "s3://world-news-test-bucket/"
            "processed/existing.json"
        ),
        duplicate_reason="url",
    )

    stored_result_two = ArticlePersistenceResult(
        status=PersistenceStatus.STORED,
        article_id=uuid4(),
        raw_s3_uri=raw_uri,
        processed_s3_uri=(
            "s3://world-news-test-bucket/"
            "processed/article-two.json"
        ),
    )

    persistence_service.persist_article.side_effect = [
        stored_result_one,
        duplicate_result,
        stored_result_two,
    ]

    rejected_uri = (
        "s3://world-news-test-bucket/"
        "rejected/gdelt/invalid.json"
    )

    persistence_service.store_rejected_payload.return_value = (
        S3ObjectLocation(
            bucket="world-news-test-bucket",
            key=(
                "rejected/gdelt/"
                "invalid.json"
            ),
            uri=rejected_uri,
        )
    )

    article_requests = [
        ArticleIngestionRequest(
            article=create_article_mock(),
            country_scores={
                "IN": Decimal("1.0000"),
            },
            state_scores={
                "IN-TG": Decimal("0.9500"),
            },
            primary_state_code="IN-TG",
            state_detection_method="keyword",
        ),
        ArticleIngestionRequest(
            article=create_article_mock(),
        ),
        ArticleIngestionRequest(
            article=create_article_mock(),
            country_scores={
                "US": Decimal("0.9000"),
            },
        ),
    ]

    rejected_items = [
        RejectedIngestionItem(
            payload={
                "title": "",
            },
            reason="Missing title",
            source_id="gdelt-record-4",
        ),
    ]

    result = await coordinator.process_batch(
        provider="GDELT",
        raw_payload={
            "articles": [
                {
                    "title": "Article one",
                },
                {
                    "title": "Article two",
                },
            ],
        },
        article_requests=article_requests,
        rejected_items=rejected_items,
        query="India technology",
    )

    assert result.provider == "GDELT"
    assert result.raw_s3_uri == raw_uri
    assert result.total_received == 4
    assert result.stored_count == 2
    assert result.duplicate_count == 1
    assert result.rejected_count == 1
    assert result.failed_count == 0
    assert len(result.article_results) == 3
    assert result.rejected_s3_uris == (
        rejected_uri,
    )
    assert result.errors == ()

    persistence_service.store_raw_payload.assert_awaited_once_with(
        provider="GDELT",
        payload={
            "articles": [
                {
                    "title": "Article one",
                },
                {
                    "title": "Article two",
                },
            ],
        },
        source_id=None,
        query="India technology",
        extra_partitions=None,
    )

    assert (
        persistence_service.persist_article.await_count
        == 3
    )

    persistence_service.store_rejected_payload.assert_awaited_once_with(
        provider="GDELT",
        payload={
            "title": "",
        },
        reason="Missing title",
        source_id="gdelt-record-4",
        extra_partitions=None,
    )


@pytest.mark.asyncio
async def test_article_failure_is_counted_and_batch_continues(
) -> None:
    """Confirm one article failure does not stop the batch."""

    coordinator, persistence_service = (
        create_coordinator()
    )

    raw_uri = (
        "s3://world-news-test-bucket/"
        "raw/rss/feed.json"
    )

    persistence_service.store_raw_payload.return_value = (
        S3ObjectLocation(
            bucket="world-news-test-bucket",
            key="raw/rss/feed.json",
            uri=raw_uri,
        )
    )

    successful_result = ArticlePersistenceResult(
        status=PersistenceStatus.STORED,
        article_id=uuid4(),
        raw_s3_uri=raw_uri,
        processed_s3_uri=(
            "s3://world-news-test-bucket/"
            "processed/success.json"
        ),
    )

    persistence_service.persist_article.side_effect = [
        ArticlePersistenceError(
            article_url=(
                "https://example.com/failed"
            ),
            detail="Database unavailable",
        ),
        successful_result,
    ]

    result = await coordinator.process_batch(
        provider="RSS",
        raw_payload={
            "items": [],
        },
        article_requests=[
            ArticleIngestionRequest(
                article=create_article_mock()
            ),
            ArticleIngestionRequest(
                article=create_article_mock()
            ),
        ],
    )

    assert result.total_received == 2
    assert result.stored_count == 1
    assert result.duplicate_count == 0
    assert result.rejected_count == 0
    assert result.failed_count == 1
    assert len(result.article_results) == 1
    assert "Database unavailable" in result.errors[0]

    assert (
        persistence_service.persist_article.await_count
        == 2
    )


@pytest.mark.asyncio
async def test_rejected_storage_failure_is_counted(
) -> None:
    """Confirm rejected-storage failures are reported."""

    coordinator, persistence_service = (
        create_coordinator()
    )

    persistence_service.store_raw_payload.return_value = (
        S3ObjectLocation(
            bucket="world-news-test-bucket",
            key="raw/rss/feed.json",
            uri=(
                "s3://world-news-test-bucket/"
                "raw/rss/feed.json"
            ),
        )
    )

    persistence_service.store_rejected_payload.side_effect = (
        RejectedPayloadPersistenceError(
            provider="RSS",
            detail="Rejected S3 layer unavailable",
        )
    )

    result = await coordinator.process_batch(
        provider="RSS",
        raw_payload={
            "items": [],
        },
        article_requests=[],
        rejected_items=[
            RejectedIngestionItem(
                payload={
                    "title": None,
                },
                reason="Invalid title",
            ),
        ],
    )

    assert result.total_received == 1
    assert result.stored_count == 0
    assert result.duplicate_count == 0
    assert result.rejected_count == 0
    assert result.failed_count == 1
    assert result.rejected_s3_uris == ()
    assert (
        "Rejected S3 layer unavailable"
        in result.errors[0]
    )


@pytest.mark.asyncio
async def test_raw_storage_failure_stops_batch(
) -> None:
    """Confirm raw storage must succeed before processing."""

    coordinator, persistence_service = (
        create_coordinator()
    )

    persistence_service.store_raw_payload.side_effect = (
        RawPayloadPersistenceError(
            provider="GDELT",
            detail="Raw S3 layer unavailable",
        )
    )

    with pytest.raises(
        RawPayloadPersistenceError,
        match="Raw S3 layer unavailable",
    ):
        await coordinator.process_batch(
            provider="GDELT",
            raw_payload={
                "articles": [],
            },
            article_requests=[
                ArticleIngestionRequest(
                    article=create_article_mock()
                ),
            ],
        )

    persistence_service.persist_article.assert_not_awaited()
    persistence_service.store_rejected_payload.assert_not_awaited()


@pytest.mark.asyncio
async def test_empty_batch_returns_zero_counts(
) -> None:
    """Confirm empty provider responses are supported."""

    coordinator, persistence_service = (
        create_coordinator()
    )

    raw_uri = (
        "s3://world-news-test-bucket/"
        "raw/rss/empty-feed.json"
    )

    persistence_service.store_raw_payload.return_value = (
        S3ObjectLocation(
            bucket="world-news-test-bucket",
            key="raw/rss/empty-feed.json",
            uri=raw_uri,
        )
    )

    result = await coordinator.process_batch(
        provider="RSS",
        raw_payload={
            "items": [],
        },
        article_requests=[],
    )

    assert result.total_received == 0
    assert result.stored_count == 0
    assert result.duplicate_count == 0
    assert result.rejected_count == 0
    assert result.failed_count == 0
    assert result.article_results == ()
    assert result.rejected_s3_uris == ()
    assert result.errors == ()

    persistence_service.persist_article.assert_not_awaited()
    persistence_service.store_rejected_payload.assert_not_awaited()
