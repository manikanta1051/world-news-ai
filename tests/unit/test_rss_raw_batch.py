from __future__ import annotations

from datetime import datetime, timezone
from email.utils import format_datetime
from types import SimpleNamespace

import pytest

from src.ingestion.feed_sources import (
    FeedFormat,
)
from src.ingestion.providers.rss import (
    RssFetchRequest,
    RssNewsProvider,
)
from src.models import NewsCategory


class FakeResponse:
    """Minimal HTTP response used by RSS tests."""

    def __init__(
        self,
        content: bytes,
    ) -> None:
        self.content = content


class FakeHttpClient:
    """Return a fixed RSS or Atom response."""

    def __init__(
        self,
        content: bytes,
    ) -> None:
        self.content = content
        self.requested_url: str | None = None

    async def get_response(
        self,
        *,
        url: str,
    ) -> FakeResponse:
        """Return the configured response."""

        self.requested_url = url

        return FakeResponse(
            self.content
        )

    async def close(self) -> None:
        """Support the provider interface."""


def create_feed_source() -> SimpleNamespace:
    """Create a feed configuration for tests."""

    return SimpleNamespace(
        source_id="example-rss",
        name="Example RSS",
        feed_url=(
            "https://example.com/rss.xml"
        ),
        homepage_url=(
            "https://example.com"
        ),
        source_country_code="IN",
        language_code="en",
        default_category=(
            NewsCategory.GENERAL
        ),
        expected_format=FeedFormat.RSS,
        max_articles_per_fetch=50,
    )


def build_rss_xml() -> str:
    """Create a feed with one valid and one invalid entry."""

    published_date = format_datetime(
        datetime.now(timezone.utc)
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Example RSS</title>
    <link>https://example.com</link>
    <description>Example feed</description>
    <item>
      <title>India technology update</title>
      <link>https://example.com/news/one</link>
      <description>Technology development in India.</description>
      <pubDate>{published_date}</pubDate>
      <guid>entry-one</guid>
    </item>
    <item>
      <title></title>
      <link>https://example.com/news/two</link>
      <description>Invalid item.</description>
      <pubDate>{published_date}</pubDate>
      <guid>entry-two</guid>
    </item>
  </channel>
</rss>
"""


def test_rss_request_normalizes_uppercase_timespan(
) -> None:
    """Confirm normalization happens before regex validation."""

    request = RssFetchRequest(
        query=" technology ",
        max_records=20,
        timespan="7D",
    )

    assert request.query == "technology"
    assert request.max_records == 20
    assert request.timespan == "7d"


@pytest.mark.asyncio
async def test_fetch_batch_preserves_raw_xml_and_rejections(
) -> None:
    """Confirm raw XML and invalid entries are retained."""

    xml_text = build_rss_xml()
    fake_client = FakeHttpClient(
        xml_text.encode("utf-8")
    )

    provider = RssNewsProvider(
        feed_source=create_feed_source(),
        http_client=fake_client,
    )

    result = await provider.fetch_batch(
        query="technology",
        max_records=20,
        timespan="7d",
    )

    assert result.provider_name == (
        "Example RSS"
    )
    assert result.received_count == 2
    assert len(result.articles) == 1
    assert len(result.rejected_items) == 1

    assert result.articles[0].title == (
        "India technology update"
    )
    assert result.articles[
        0
    ].source.country_code == "IN"

    raw_payload = result.raw_payload

    assert isinstance(
        raw_payload,
        dict,
    )
    assert raw_payload["source_id"] == (
        "example-rss"
    )
    assert raw_payload["content"] == (
        xml_text
    )
    assert raw_payload[
        "content_length"
    ] == len(
        xml_text.encode("utf-8")
    )

    rejected = result.rejected_items[0]

    assert (
        "title cannot be empty"
        in rejected.reason
    )
    assert rejected.source_id == (
        "entry-two"
    )

    assert fake_client.requested_url == (
        "https://example.com/rss.xml"
    )


@pytest.mark.asyncio
async def test_fetch_articles_keeps_legacy_interface(
) -> None:
    """Confirm fetch_articles returns validated articles only."""

    provider = RssNewsProvider(
        feed_source=create_feed_source(),
        http_client=FakeHttpClient(
            build_rss_xml().encode(
                "utf-8"
            )
        ),
    )

    articles = await provider.fetch_articles(
        query="technology",
        max_records=20,
        timespan="7d",
    )

    assert len(articles) == 1
    assert articles[0].title == (
        "India technology update"
    )


@pytest.mark.asyncio
async def test_fetch_batch_applies_query_filter(
) -> None:
    """Confirm unmatched valid entries are filtered, not rejected."""

    provider = RssNewsProvider(
        feed_source=create_feed_source(),
        http_client=FakeHttpClient(
            build_rss_xml().encode(
                "utf-8"
            )
        ),
    )

    result = await provider.fetch_batch(
        query="sports",
        max_records=20,
        timespan="7d",
    )

    assert result.received_count == 2
    assert result.articles == ()
    assert len(
        result.rejected_items
    ) == 1
