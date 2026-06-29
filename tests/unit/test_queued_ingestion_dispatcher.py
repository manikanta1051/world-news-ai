from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.ingestion.provider_result import (
    ProviderFetchResult,
    ProviderRejectedItem,
)
from src.messaging import (
    ArticleProcessingMessage,
    SqsPublisherError,
    SqsSendResult,
)
from src.models import (
    Article,
    NewsCategory,
    NewsSource,
    SourceType,
)
from src.services import (
    QueuedIngestionDispatcher,
    RejectedPayloadPersistenceError,
)
from src.storage.s3_service import (
    S3ObjectLocation,
)


def create_article(
    *,
    country_code: str | None = "IN",
) -> Article:
    """Create a valid article for dispatcher tests."""

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
            country_code=country_code,
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
    )


def create_dispatcher() -> tuple[
    QueuedIngestionDispatcher,
    Mock,
    Mock,
]:
    """Create a dispatcher with mocked dependencies."""

    storage_service = Mock()
    storage_service.store_raw_payload = AsyncMock()
    storage_service.store_rejected_payload = (
        AsyncMock()
    )

    publisher = Mock()
    publisher.publish = Mock()

    dispatcher = QueuedIngestionDispatcher(
        storage_service=storage_service,
        publisher=publisher,
    )

    return (
        dispatcher,
        storage_service,
        publisher,
    )


@pytest.mark.asyncio
async def test_dispatch_stores_raw_and_queues_articles(
) -> None:
    """Confirm validated articles are queued."""

    (
        dispatcher,
        storage_service,
        publisher,
    ) = create_dispatcher()

    provider = Mock()
    provider.provider_name = "GDELT"
    provider.fetch_batch = AsyncMock()

    articles = (
        create_article(country_code="IN"),
        create_article(country_code="US"),
    )

    provider.fetch_batch.return_value = (
        ProviderFetchResult(
            provider_name="GDELT",
            raw_payload={
                "articles": [
                    {
                        "title": "One",
                    },
                    {
                        "title": "Two",
                    },
                ],
            },
            articles=articles,
            received_count=3,
            rejected_items=(
                ProviderRejectedItem(
                    payload={
                        "title": "",
                    },
                    reason="title cannot be empty",
                    source_id="gdelt-3",
                ),
            ),
        )
    )

    storage_service.store_raw_payload.return_value = (
        S3ObjectLocation(
            bucket="world-news-test",
            key="raw/gdelt/run.json",
            uri=(
                "s3://world-news-test/"
                "raw/gdelt/run.json"
            ),
        )
    )

    storage_service.store_rejected_payload.return_value = (
        S3ObjectLocation(
            bucket="world-news-test",
            key="rejected/gdelt/invalid.json",
            uri=(
                "s3://world-news-test/"
                "rejected/gdelt/invalid.json"
            ),
        )
    )

    publisher.publish.side_effect = [
        SqsSendResult(
            message_id="message-1"
        ),
        SqsSendResult(
            message_id="message-2"
        ),
    ]

    result = await dispatcher.dispatch(
        provider=provider,
        query="India technology",
        max_records=20,
        timespan="24h",
        source_id="gdelt",
    )

    assert result.received_count == 3
    assert result.validated_count == 2
    assert result.queued_count == 2
    assert result.rejected_count == 1
    assert result.failed_count == 0
    assert result.sqs_message_ids == (
        "message-1",
        "message-2",
    )

    assert publisher.publish.call_count == 2

    first_message = (
        publisher.publish
        .call_args_list[0]
        .kwargs["message"]
    )

    assert isinstance(
        first_message,
        ArticleProcessingMessage,
    )

    assert first_message.raw_s3_uri == (
        "s3://world-news-test/"
        "raw/gdelt/run.json"
    )

    assert first_message.country_scores == {
        "IN": Decimal("1.0000"),
    }

    storage_service.store_rejected_payload.assert_awaited_once_with(
        provider="GDELT",
        payload={
            "title": "",
        },
        reason="title cannot be empty",
        source_id="gdelt-3",
        extra_partitions=None,
    )


@pytest.mark.asyncio
async def test_publish_failure_is_counted_and_continues(
) -> None:
    """Confirm one SQS failure does not stop the batch."""

    (
        dispatcher,
        storage_service,
        publisher,
    ) = create_dispatcher()

    provider = Mock()
    provider.provider_name = "GDELT"
    provider.fetch_batch = AsyncMock(
        return_value=ProviderFetchResult(
            provider_name="GDELT",
            raw_payload={
                "articles": [],
            },
            articles=(
                create_article(),
                create_article(),
            ),
            received_count=2,
        )
    )

    storage_service.store_raw_payload.return_value = (
        S3ObjectLocation(
            bucket="bucket",
            key="raw/run.json",
            uri="s3://bucket/raw/run.json",
        )
    )

    publisher.publish.side_effect = [
        SqsPublisherError(
            queue_url="queue-url",
            detail="SQS unavailable",
        ),
        SqsSendResult(
            message_id="message-2"
        ),
    ]

    result = await dispatcher.dispatch(
        provider=provider,
        query="news",
    )

    assert result.queued_count == 1
    assert result.failed_count == 1

    assert "SQS unavailable" in (
        result.errors[0]
    )


@pytest.mark.asyncio
async def test_rejected_storage_failure_is_counted(
) -> None:
    """Confirm rejected-storage failures are recorded."""

    (
        dispatcher,
        storage_service,
        publisher,
    ) = create_dispatcher()

    provider = Mock()
    provider.provider_name = "RSS"
    provider.fetch_batch = AsyncMock(
        return_value=ProviderFetchResult(
            provider_name="RSS",
            raw_payload={
                "content": "<rss />",
            },
            articles=(),
            received_count=1,
            rejected_items=(
                ProviderRejectedItem(
                    payload={
                        "title": "",
                    },
                    reason="invalid title",
                ),
            ),
        )
    )

    storage_service.store_raw_payload.return_value = (
        S3ObjectLocation(
            bucket="bucket",
            key="raw/rss.xml",
            uri="s3://bucket/raw/rss.xml",
        )
    )

    storage_service.store_rejected_payload.side_effect = (
        RejectedPayloadPersistenceError(
            provider="RSS",
            detail="Rejected layer unavailable",
        )
    )

    result = await dispatcher.dispatch(
        provider=provider,
        query="India",
    )

    assert result.queued_count == 0
    assert result.rejected_count == 0
    assert result.failed_count == 1

    assert (
        "Rejected layer unavailable"
        in result.errors[0]
    )

    publisher.publish.assert_not_called()


@pytest.mark.asyncio
async def test_custom_message_factory_is_supported(
) -> None:
    """Confirm state enrichment can be injected."""

    (
        dispatcher,
        storage_service,
        publisher,
    ) = create_dispatcher()

    article = create_article()

    provider = Mock()
    provider.provider_name = "GDELT"
    provider.fetch_batch = AsyncMock(
        return_value=ProviderFetchResult(
            provider_name="GDELT",
            raw_payload={
                "articles": [],
            },
            articles=(article,),
            received_count=1,
        )
    )

    storage_service.store_raw_payload.return_value = (
        S3ObjectLocation(
            bucket="bucket",
            key="raw/run.json",
            uri="s3://bucket/raw/run.json",
        )
    )

    publisher.publish.return_value = (
        SqsSendResult(
            message_id="message-1"
        )
    )

    def message_factory(
        article_value: Article,
        provider_name: str,
        raw_s3_uri: str,
    ) -> ArticleProcessingMessage:
        return ArticleProcessingMessage(
            provider=provider_name,
            raw_s3_uri=raw_s3_uri,
            article_payload=(
                article_value.model_dump(
                    mode="json"
                )
            ),
            country_scores={
                "IN": 1,
            },
            state_scores={
                "IN-TG": 0.95,
            },
            primary_state_code="IN-TG",
            state_detection_method="test",
        )

    await dispatcher.dispatch(
        provider=provider,
        query="Telangana",
        message_factory=message_factory,
    )

    published_message = (
        publisher.publish
        .call_args
        .kwargs["message"]
    )

    assert published_message.state_scores == {
        "IN-TG": Decimal("0.95"),
    }

    assert (
        published_message.primary_state_code
        == "IN-TG"
    )

    assert (
        published_message.state_detection_method
        == "test"
    )


@pytest.mark.asyncio
async def test_dispatch_validates_inputs(
) -> None:
    """Confirm invalid dispatch options are rejected."""

    (
        dispatcher,
        storage_service,
        publisher,
    ) = create_dispatcher()

    provider = Mock()
    provider.provider_name = "GDELT"
    provider.fetch_batch = AsyncMock()

    with pytest.raises(
        ValueError,
        match="at least 1",
    ):
        await dispatcher.dispatch(
            provider=provider,
            query="news",
            max_records=0,
        )

    provider.fetch_batch.assert_not_awaited()

    storage_service.store_raw_payload.assert_not_awaited()

    publisher.publish.assert_not_called()