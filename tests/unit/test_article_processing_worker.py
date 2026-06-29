from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.messaging import ArticleProcessingMessage
from src.models import (
    Article,
    NewsCategory,
    NewsSource,
    SourceType,
)
from src.services import (
    ArticlePersistenceError,
    ArticlePersistenceResult,
    ArticleProcessingWorker,
    ArticleProcessingWorkerError,
    IngestionPersistenceService,
    PersistenceStatus,
)


def create_article() -> Article:
    """Create one valid article for worker tests."""

    return Article(
        article_id=uuid4(),
        title="India technology update",
        description="Technology development.",
        content="Detailed technology article.",
        url=(
            "https://example.com/"
            f"article-{uuid4()}"
        ),
        source=NewsSource(
            name="Example News",
            source_type=SourceType.GDELT,
            homepage_url="https://example.com",
            country_code="IN",
        ),
        published_at=datetime(
            2026,
            6,
            29,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        primary_category=NewsCategory.GENERAL,
        language_code="en",
        content_hash="b" * 64,
    )


def create_worker() -> tuple[
    ArticleProcessingWorker,
    Mock,
]:
    """Create a worker with mocked persistence."""

    persistence_service = Mock(
        spec=IngestionPersistenceService
    )
    persistence_service.persist_article = (
        AsyncMock()
    )

    worker = ArticleProcessingWorker(
        persistence_service=(
            persistence_service
        )
    )

    return worker, persistence_service


def create_message(
    article: Article,
) -> ArticleProcessingMessage:
    """Create one valid article-processing message."""

    return ArticleProcessingMessage(
        provider="GDELT",
        raw_s3_uri=(
            "s3://world-news-test/"
            "raw/gdelt/response.json"
        ),
        article_payload=article.model_dump(
            mode="json"
        ),
        country_scores={
            "IN": Decimal("1.0000"),
        },
        state_scores={
            "IN-TG": Decimal("0.9500"),
        },
        primary_state_code="IN-TG",
        state_detection_method="keyword",
    )


@pytest.mark.asyncio
async def test_worker_persists_article_message(
) -> None:
    """Confirm one queue message is persisted."""

    worker, persistence_service = (
        create_worker()
    )

    article = create_article()
    message = create_message(article)

    expected_result = ArticlePersistenceResult(
        status=PersistenceStatus.STORED,
        article_id=article.article_id,
        raw_s3_uri=message.raw_s3_uri,
        processed_s3_uri=(
            "s3://world-news-test/"
            "processed/article.json"
        ),
        source_created=True,
    )

    persistence_service.persist_article.return_value = (
        expected_result
    )

    result = await worker.process_message(
        message=message
    )

    assert result.message_id == (
        message.message_id
    )
    assert result.persistence_result == (
        expected_result
    )

    persistence_service.persist_article.assert_awaited_once_with(
        article=article,
        raw_s3_uri=message.raw_s3_uri,
        country_scores={
            "IN": Decimal("1.0000"),
        },
        state_scores={
            "IN-TG": Decimal("0.9500"),
        },
        primary_state_code="IN-TG",
        state_detection_method="keyword",
    )


@pytest.mark.asyncio
async def test_worker_returns_duplicate_result(
) -> None:
    """Confirm duplicate results remain successful."""

    worker, persistence_service = (
        create_worker()
    )

    article = create_article()
    message = create_message(article)

    duplicate_result = ArticlePersistenceResult(
        status=PersistenceStatus.DUPLICATE,
        article_id=uuid4(),
        raw_s3_uri=message.raw_s3_uri,
        processed_s3_uri=(
            "s3://world-news-test/"
            "processed/existing.json"
        ),
        duplicate_reason="url",
    )

    persistence_service.persist_article.return_value = (
        duplicate_result
    )

    result = await worker.process_message(
        message=message
    )

    assert result.persistence_result.status == (
        PersistenceStatus.DUPLICATE
    )
    assert (
        result.persistence_result
        .duplicate_reason
        == "url"
    )


@pytest.mark.asyncio
async def test_worker_processes_serialized_message(
) -> None:
    """Confirm the worker accepts an SQS JSON body."""

    worker, persistence_service = (
        create_worker()
    )

    article = create_article()
    message = create_message(article)

    persistence_service.persist_article.return_value = (
        ArticlePersistenceResult(
            status=PersistenceStatus.STORED,
            article_id=article.article_id,
            raw_s3_uri=message.raw_s3_uri,
            processed_s3_uri=(
                "s3://world-news-test/"
                "processed/article.json"
            ),
        )
    )

    result = await worker.process_json(
        message.to_json()
    )

    assert result.message_id == (
        message.message_id
    )


@pytest.mark.asyncio
async def test_worker_rejects_invalid_article_payload(
) -> None:
    """Confirm malformed article data is rejected."""

    worker, persistence_service = (
        create_worker()
    )

    message = ArticleProcessingMessage(
        provider="GDELT",
        raw_s3_uri=(
            "s3://world-news-test/"
            "raw/gdelt/response.json"
        ),
        article_payload={
            "title": "Missing required fields",
        },
    )

    with pytest.raises(
        ArticleProcessingWorkerError,
        match="Invalid article payload",
    ):
        await worker.process_message(
            message=message
        )

    persistence_service.persist_article.assert_not_awaited()


@pytest.mark.asyncio
async def test_worker_converts_persistence_failure(
) -> None:
    """Confirm persistence failures use a worker error."""

    worker, persistence_service = (
        create_worker()
    )

    article = create_article()
    message = create_message(article)

    persistence_service.persist_article.side_effect = (
        ArticlePersistenceError(
            article_url=str(article.url),
            detail="Database unavailable",
        )
    )

    with pytest.raises(
        ArticleProcessingWorkerError,
        match="Database unavailable",
    ):
        await worker.process_message(
            message=message
        )


@pytest.mark.asyncio
async def test_worker_rejects_invalid_message_json(
) -> None:
    """Confirm malformed SQS JSON is rejected."""

    worker, persistence_service = (
        create_worker()
    )

    with pytest.raises(
        ArticleProcessingWorkerError,
        match="Invalid ArticleProcessingMessage",
    ):
        await worker.process_json(
            '{"provider": "GDELT"}'
        )

    persistence_service.persist_article.assert_not_awaited()