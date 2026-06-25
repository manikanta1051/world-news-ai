import pytest
from pydantic import ValidationError

from src.ingestion import (
    FEED_SOURCES,
    FeedFormat,
    FeedSourceConfig,
    get_enabled_feed_sources,
    get_feed_source,
    validate_feed_registry,
)
from src.models import NewsCategory


def test_feed_registry_contains_enabled_sources() -> None:
    """Confirm that the default registry contains usable sources."""

    enabled_sources = get_enabled_feed_sources()

    assert len(enabled_sources) >= 1
    assert all(source.enabled for source in enabled_sources)
    assert all(source.source_id for source in FEED_SOURCES)


def test_feed_source_can_be_found_by_id() -> None:
    """Confirm that source lookup accepts normalized IDs."""

    source = get_feed_source(
        " NASA-TECHNOLOGY "
    )

    assert source.source_id == "nasa-technology"
    assert source.name == "NASA Technology"
    assert (
        source.default_category
        == NewsCategory.TECHNOLOGY_AI
    )


def test_unknown_feed_source_is_rejected() -> None:
    """Confirm that an unknown source ID raises KeyError."""

    with pytest.raises(KeyError):
        get_feed_source("unknown-feed")


def test_feed_source_normalizes_country_code() -> None:
    """Confirm that publisher country codes are normalized."""

    source = FeedSourceConfig(
        source_id="example-source",
        name="Example Source",
        feed_url="https://example.com/feed.xml",
        homepage_url="https://example.com",
        source_country_code="us",
        expected_format=FeedFormat.RSS,
    )

    assert source.source_country_code == "US"


def test_invalid_feed_source_id_is_rejected() -> None:
    """Confirm that source IDs follow the slug format."""

    with pytest.raises(ValidationError):
        FeedSourceConfig(
            source_id="Invalid Source ID",
            name="Example Source",
            feed_url="https://example.com/feed.xml",
            homepage_url="https://example.com",
        )


def test_duplicate_source_ids_are_rejected() -> None:
    """Confirm that the registry rejects repeated source IDs."""

    first_source = FeedSourceConfig(
        source_id="duplicate-source",
        name="First Source",
        feed_url="https://example.com/feed-one.xml",
        homepage_url="https://example.com",
    )

    second_source = FeedSourceConfig(
        source_id="duplicate-source",
        name="Second Source",
        feed_url="https://example.org/feed-two.xml",
        homepage_url="https://example.org",
    )

    with pytest.raises(
        ValueError,
        match="Duplicate feed source ID",
    ):
        validate_feed_registry(
            (
                first_source,
                second_source,
            )
        )


def test_duplicate_feed_urls_are_rejected() -> None:
    """Confirm that the registry rejects repeated feed URLs."""

    first_source = FeedSourceConfig(
        source_id="first-source",
        name="First Source",
        feed_url="https://example.com/feed.xml",
        homepage_url="https://example.com",
    )

    second_source = FeedSourceConfig(
        source_id="second-source",
        name="Second Source",
        feed_url="https://example.com/feed.xml",
        homepage_url="https://example.org",
    )

    with pytest.raises(
        ValueError,
        match="Duplicate feed URL",
    ):
        validate_feed_registry(
            (
                first_source,
                second_source,
            )
        )