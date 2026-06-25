from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
)

from src.models import (
    NewsCategory,
    normalize_country_code,
)


class FeedFormat(StrEnum):
    """Expected syndication format for a configured feed."""

    AUTO = "auto"
    RSS = "rss"
    ATOM = "atom"


class FeedSourceConfig(BaseModel):
    """Validated configuration for one RSS or Atom feed."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
        validate_assignment=True,
        frozen=True,
    )

    source_id: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )

    name: str = Field(
        min_length=2,
        max_length=200,
    )

    feed_url: HttpUrl

    homepage_url: HttpUrl

    source_country_code: str | None = None

    default_category: NewsCategory = NewsCategory.GENERAL

    language_code: str = Field(
        default="en",
        pattern=r"^[a-z]{2,3}(-[A-Z]{2})?$",
    )

    expected_format: FeedFormat = FeedFormat.AUTO

    is_official_source: bool = False

    enabled: bool = True

    max_articles_per_fetch: int = Field(
        default=50,
        ge=1,
        le=200,
    )

    @field_validator("source_country_code")
    @classmethod
    def validate_source_country_code(
        cls,
        value: str | None,
    ) -> str | None:
        """Normalize and validate the publisher country code."""

        if value is None:
            return None

        return normalize_country_code(value)


FEED_SOURCES: tuple[FeedSourceConfig, ...] = (
    FeedSourceConfig(
        source_id="nasa-recently-published",
        name="NASA Recently Published",
        feed_url="https://www.nasa.gov/feed/",
        homepage_url="https://www.nasa.gov/",
        source_country_code="US",
        default_category=NewsCategory.SCIENCE_SPACE,
        language_code="en",
        expected_format=FeedFormat.RSS,
        is_official_source=True,
        max_articles_per_fetch=50,
    ),
    FeedSourceConfig(
        source_id="nasa-news-releases",
        name="NASA News Releases",
        feed_url="https://www.nasa.gov/news-release/feed/",
        homepage_url="https://www.nasa.gov/news-release/",
        source_country_code="US",
        default_category=NewsCategory.SCIENCE_SPACE,
        language_code="en",
        expected_format=FeedFormat.RSS,
        is_official_source=True,
        max_articles_per_fetch=50,
    ),
    FeedSourceConfig(
        source_id="nasa-technology",
        name="NASA Technology",
        feed_url="https://www.nasa.gov/technology/feed/",
        homepage_url="https://www.nasa.gov/technology/",
        source_country_code="US",
        default_category=NewsCategory.TECHNOLOGY_AI,
        language_code="en",
        expected_format=FeedFormat.RSS,
        is_official_source=True,
        max_articles_per_fetch=50,
    ),
    FeedSourceConfig(
        source_id="nasa-jpl-news",
        name="NASA Jet Propulsion Laboratory News",
        feed_url="https://www.jpl.nasa.gov/feeds/news/",
        homepage_url="https://www.jpl.nasa.gov/news/",
        source_country_code="US",
        default_category=NewsCategory.SCIENCE_SPACE,
        language_code="en",
        expected_format=FeedFormat.RSS,
        is_official_source=True,
        max_articles_per_fetch=50,
    ),
)


def validate_feed_registry(
    feed_sources: tuple[FeedSourceConfig, ...],
) -> None:
    """Ensure that source IDs and feed URLs are unique."""

    source_ids: set[str] = set()
    feed_urls: set[str] = set()

    for source in feed_sources:
        if source.source_id in source_ids:
            raise ValueError(
                "Duplicate feed source ID: "
                f"{source.source_id}"
            )

        feed_url = str(source.feed_url)

        if feed_url in feed_urls:
            raise ValueError(
                f"Duplicate feed URL: {feed_url}"
            )

        source_ids.add(source.source_id)
        feed_urls.add(feed_url)


def get_enabled_feed_sources() -> list[FeedSourceConfig]:
    """Return all feeds currently enabled for ingestion."""

    return [
        source
        for source in FEED_SOURCES
        if source.enabled
    ]


def get_feed_source(
    source_id: str,
) -> FeedSourceConfig:
    """Find one configured feed by its source ID."""

    normalized_id = source_id.strip().lower()

    for source in FEED_SOURCES:
        if source.source_id == normalized_id:
            return source

    raise KeyError(
        f"Unknown feed source ID: {normalized_id}"
    )


validate_feed_registry(FEED_SOURCES)