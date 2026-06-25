import asyncio
from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from pydantic import ValidationError

import src.ingestion.providers.rss as rss_module
from src.ingestion import (
    FeedFormat,
    FeedSourceConfig,
    NewsProviderResponseError,
    RssFetchRequest,
    RssNewsProvider,
    clean_html_text,
    timespan_to_timedelta,
)
from src.models import (
    NewsCategory,
    SourceType,
)


FIXTURE_DIRECTORY = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
)

RSS_FIXTURE = (
    FIXTURE_DIRECTORY
    / "rss_feed.xml"
)

MALFORMED_FIXTURE = (
    FIXTURE_DIRECTORY
    / "malformed_feed.xml"
)


class FakeHttpClient:
    """Return predefined RSS response content."""

    def __init__(self, content: bytes) -> None:
        self.content = content
        self.requested_url: str | None = None
        self.closed = False

    async def get_response(
        self,
        url: str,
        params: object | None = None,
    ) -> httpx.Response:
        """Return a successful fake HTTP response."""

        self.requested_url = url

        request = httpx.Request(
            "GET",
            url,
        )

        return httpx.Response(
            status_code=200,
            content=self.content,
            request=request,
        )

    async def close(self) -> None:
        """Record that close was called."""

        self.closed = True


def create_test_source() -> FeedSourceConfig:
    """Create a deterministic source for provider tests."""

    return FeedSourceConfig(
        source_id="test-technology-feed",
        name="Test Technology Feed",
        feed_url="https://example.com/feed.xml",
        homepage_url="https://example.com",
        source_country_code="US",
        default_category=NewsCategory.TECHNOLOGY_AI,
        language_code="en",
        expected_format=FeedFormat.RSS,
        is_official_source=True,
        max_articles_per_fetch=50,
    )


def fixed_current_time() -> datetime:
    """Return a fixed UTC time for timespan tests."""

    return datetime(
        2026,
        6,
        25,
        12,
        0,
        tzinfo=timezone.utc,
    )


def test_clean_html_text_removes_tags_and_scripts() -> None:
    """Confirm that HTML becomes readable plain text."""

    result = clean_html_text(
        """
        <p>NASA <strong>tests</strong> a system.</p>
        <script>ignore_this()</script>
        """
    )

    assert result == "NASA tests a system."


def test_timespan_conversion() -> None:
    """Confirm that supported timespans are converted."""

    assert timespan_to_timedelta(
        "24h"
    ).total_seconds() == 86400

    assert timespan_to_timedelta(
        "7d"
    ).days == 7

    assert timespan_to_timedelta(
        "2weeks"
    ).days == 14

    assert timespan_to_timedelta(
        "3months"
    ).days == 90


def test_invalid_rss_request_is_rejected() -> None:
    """Confirm that invalid request limits and timespans fail."""

    with pytest.raises(ValidationError):
        RssFetchRequest(
            max_records=0,
        )

    with pytest.raises(ValidationError):
        RssFetchRequest(
            timespan="invalid",
        )


def test_rss_provider_maps_filters_and_deduplicates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirm mapping, timespan filtering, and URL deduplication."""

    monkeypatch.setattr(
        rss_module,
        "current_utc_time",
        fixed_current_time,
    )

    fake_client = FakeHttpClient(
        RSS_FIXTURE.read_bytes()
    )

    provider = RssNewsProvider(
        feed_source=create_test_source(),
        http_client=fake_client,
    )

    articles = asyncio.run(
        provider.fetch_articles(
            max_records=10,
            timespan="7d",
        )
    )

    assert len(articles) == 2

    first_article = articles[0]

    assert first_article.title == (
        "NASA develops new space communication technology"
    )
    assert first_article.description == (
        "NASA is testing a new "
        "space communication system."
    )
    assert first_article.content == (
        "The technology may improve communication "
        "between Earth and future spacecraft."
    )
    assert first_article.author == "NASA Technology Team"
    assert str(first_article.image_url) == (
        "https://example.com/images/space-system.jpg"
    )
    assert (
        first_article.primary_category
        == NewsCategory.TECHNOLOGY_AI
    )
    assert (
        first_article.source.source_type
        == SourceType.RSS
    )
    assert first_article.source.country_code == "US"
    assert first_article.published_at == datetime(
        2026,
        6,
        24,
        14,
        30,
        tzinfo=timezone.utc,
    )

    second_article = articles[1]

    assert second_article.title == (
        "New lunar science mission prepares for launch"
    )
    assert str(second_article.image_url) == (
        "https://example.com/images/lunar-mission.png"
    )

    urls = {
        str(article.url)
        for article in articles
    }

    assert len(urls) == 2
    assert fake_client.requested_url == (
        "https://example.com/feed.xml"
    )


def test_rss_provider_applies_query_filter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirm that query matching uses article text."""

    monkeypatch.setattr(
        rss_module,
        "current_utc_time",
        fixed_current_time,
    )

    fake_client = FakeHttpClient(
        RSS_FIXTURE.read_bytes()
    )

    provider = RssNewsProvider(
        feed_source=create_test_source(),
        http_client=fake_client,
    )

    articles = asyncio.run(
        provider.fetch_articles(
            query="lunar",
            max_records=10,
            timespan="7d",
        )
    )

    assert len(articles) == 1
    assert "lunar" in articles[0].title.casefold()


def test_provider_respects_source_article_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirm that source limits override larger request limits."""

    monkeypatch.setattr(
        rss_module,
        "current_utc_time",
        fixed_current_time,
    )

    limited_source = create_test_source().model_copy(
        update={
            "max_articles_per_fetch": 1,
        }
    )

    fake_client = FakeHttpClient(
        RSS_FIXTURE.read_bytes()
    )

    provider = RssNewsProvider(
        feed_source=limited_source,
        http_client=fake_client,
    )

    articles = asyncio.run(
        provider.fetch_articles(
            max_records=10,
            timespan="7d",
        )
    )

    assert len(articles) == 1


def test_malformed_feed_without_entries_is_rejected() -> None:
    """Confirm that unusable feed content raises a provider error."""

    fake_client = FakeHttpClient(
        MALFORMED_FIXTURE.read_bytes()
    )

    provider = RssNewsProvider(
        feed_source=create_test_source(),
        http_client=fake_client,
    )

    with pytest.raises(
        NewsProviderResponseError
    ):
        asyncio.run(
            provider.fetch_articles(
                max_records=10,
                timespan="7d",
            )
        )


def test_provider_does_not_close_injected_client() -> None:
    """Confirm that externally supplied clients remain caller-owned."""

    fake_client = FakeHttpClient(
        RSS_FIXTURE.read_bytes()
    )

    provider = RssNewsProvider(
        feed_source=create_test_source(),
        http_client=fake_client,
    )

    asyncio.run(provider.close())

    assert fake_client.closed is False