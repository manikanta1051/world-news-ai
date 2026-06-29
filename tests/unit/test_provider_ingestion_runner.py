from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.ingestion.provider_result import (
    ProviderFetchResult,
    ProviderRejectedItem,
)
from src.models import (
    Article,
    NewsCategory,
    NewsSource,
    SourceType,
)
from src.services import (
    ArticleIngestionRequest,
    BatchIngestionCoordinator,
    BatchIngestionResult,
    ProviderIngestionRunner,
    default_article_request_factory,
)


def create_article(
    *,
    country_code: str | None = "IN",
) -> Article:
    """Create one valid provider article."""

    return Article(
        article_id=uuid4(),
        title="India technology update",
        description="A technology development.",
        content="Detailed technology news.",
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
            28,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        primary_category=NewsCategory.GENERAL,
        language_code="en",
    )


def create_batch_result(
    *,
    provider: str,
    total_received: int,
) -> BatchIngestionResult:
    """Create a batch result for runner tests."""

    return BatchIngestionResult(
        provider=provider,
        raw_s3_uri="s3://bucket/raw/run.json",
        total_received=total_received,
        stored_count=total_received,
        duplicate_count=0,
        rejected_count=0,
        failed_count=0,
        article_results=(),
        rejected_s3_uris=(),
        errors=(),
    )


def create_runner() -> tuple[
    ProviderIngestionRunner,
    Mock,
]:
    """Create the runner with a mocked coordinator."""

    coordinator = Mock(
        spec=BatchIngestionCoordinator
    )
    coordinator.process_batch = AsyncMock()

    runner = ProviderIngestionRunner(
        coordinator=coordinator
    )

    return runner, coordinator


@pytest.mark.asyncio
async def test_runner_uses_raw_provider_batch(
) -> None:
    """Confirm exact raw data and rejections reach persistence."""

    runner, coordinator = create_runner()

    provider = Mock(
        spec=[
            "provider_name",
            "fetch_batch",
            "fetch_articles",
        ]
    )
    provider.provider_name = "GDELT"
    provider.fetch_batch = AsyncMock()
    provider.fetch_articles = AsyncMock()

    articles = [
        create_article(country_code="IN"),
        create_article(country_code="US"),
    ]

    raw_payload = {
        "articles": [
            {
                "title": "Valid article",
            },
            {
                "title": "",
            },
        ],
    }

    provider.fetch_batch.return_value = (
        ProviderFetchResult(
            provider_name="GDELT",
            raw_payload=raw_payload,
            articles=tuple(articles),
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

    coordinator.process_batch.return_value = (
        create_batch_result(
            provider="GDELT",
            total_received=3,
        )
    )

    result = await runner.run(
        provider=provider,
        query="India technology",
        max_records=20,
        timespan="24h",
        source_id="gdelt",
        extra_partitions={
            "environment": "test",
        },
    )

    assert result.provider_name == "GDELT"
    assert result.received_count == 3
    assert result.fetched_count == 2
    assert result.rejected_count == 1

    provider.fetch_batch.assert_awaited_once_with(
        query="India technology",
        max_records=20,
        timespan="24h",
    )
    provider.fetch_articles.assert_not_awaited()

    call_kwargs = (
        coordinator.process_batch.await_args.kwargs
    )

    assert call_kwargs[
        "raw_payload"
    ] is raw_payload

    article_requests = call_kwargs[
        "article_requests"
    ]

    assert len(article_requests) == 2
    assert article_requests[
        0
    ].country_scores == {
        "IN": Decimal("1.0000"),
    }
    assert article_requests[
        1
    ].country_scores == {
        "US": Decimal("1.0000"),
    }

    rejected_items = call_kwargs[
        "rejected_items"
    ]

    assert len(rejected_items) == 1
    assert rejected_items[0].payload == {
        "title": "",
    }
    assert rejected_items[0].reason == (
        "title cannot be empty"
    )
    assert rejected_items[0].source_id == (
        "gdelt-3"
    )


@pytest.mark.asyncio
async def test_runner_falls_back_to_fetch_articles(
) -> None:
    """Confirm older providers remain supported."""

    runner, coordinator = create_runner()

    provider = Mock(
        spec=[
            "provider_name",
            "fetch_articles",
        ]
    )
    provider.provider_name = "Legacy RSS"
    provider.fetch_articles = AsyncMock(
        return_value=[
            create_article(country_code="IN")
        ]
    )

    coordinator.process_batch.return_value = (
        create_batch_result(
            provider="Legacy RSS",
            total_received=1,
        )
    )

    result = await runner.run(
        provider=provider,
        query="India",
        timespan="7d",
    )

    assert result.received_count == 1
    assert result.fetched_count == 1
    assert result.rejected_count == 0

    provider.fetch_articles.assert_awaited_once_with(
        query="India",
        max_records=25,
        timespan="7d",
    )

    call_kwargs = (
        coordinator.process_batch.await_args.kwargs
    )

    snapshot = call_kwargs["raw_payload"]

    assert snapshot["provider"] == (
        "Legacy RSS"
    )
    assert snapshot["validated_count"] == 1
    assert call_kwargs["rejected_items"] == ()


@pytest.mark.asyncio
async def test_runner_supports_custom_request_factory(
) -> None:
    """Confirm location enrichment can be injected."""

    runner, coordinator = create_runner()

    provider = Mock(
        spec=[
            "provider_name",
            "fetch_articles",
        ]
    )
    provider.provider_name = "Example RSS"
    provider.fetch_articles = AsyncMock(
        return_value=[
            create_article(country_code="IN")
        ]
    )

    coordinator.process_batch.return_value = (
        create_batch_result(
            provider="Example RSS",
            total_received=1,
        )
    )

    def request_factory(
        article: Article,
    ) -> ArticleIngestionRequest:
        return ArticleIngestionRequest(
            article=article,
            country_scores={
                "IN": Decimal("1.0000"),
            },
            state_scores={
                "IN-TG": Decimal("0.9500"),
            },
            primary_state_code="IN-TG",
            state_detection_method="test",
        )

    await runner.run(
        provider=provider,
        query="Telangana",
        timespan="7d",
        request_factory=request_factory,
    )

    call_kwargs = (
        coordinator.process_batch.await_args.kwargs
    )

    request = call_kwargs[
        "article_requests"
    ][0]

    assert request.state_scores == {
        "IN-TG": Decimal("0.9500"),
    }
    assert request.primary_state_code == (
        "IN-TG"
    )


def test_default_factory_uses_source_country(
) -> None:
    """Confirm source country becomes a mapping."""

    article = create_article(
        country_code=" in "
    )

    request = (
        default_article_request_factory(
            article
        )
    )

    assert request.country_scores == {
        "IN": Decimal("1.0000"),
    }


def test_default_factory_allows_missing_country(
) -> None:
    """Confirm articles can omit source country."""

    article = create_article(
        country_code=None
    )

    request = (
        default_article_request_factory(
            article
        )
    )

    assert request.country_scores is None


@pytest.mark.asyncio
async def test_runner_validates_inputs(
) -> None:
    """Confirm invalid runner options are rejected."""

    runner, coordinator = create_runner()

    provider = Mock(
        spec=[
            "provider_name",
            "fetch_articles",
        ]
    )
    provider.provider_name = "GDELT"
    provider.fetch_articles = AsyncMock()

    with pytest.raises(
        ValueError,
        match="at least 1",
    ):
        await runner.run(
            provider=provider,
            query="news",
            max_records=0,
        )

    with pytest.raises(
        ValueError,
        match="timespan cannot be empty",
    ):
        await runner.run(
            provider=provider,
            query="news",
            timespan="   ",
        )

    provider.fetch_articles.assert_not_awaited()
    coordinator.process_batch.assert_not_awaited()
