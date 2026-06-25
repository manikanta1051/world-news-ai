import calendar
import html
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from typing import Any

import feedparser
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    TypeAdapter,
    ValidationError,
    field_validator,
)

from src.common.logging_config import logger
from src.ingestion.exceptions import NewsProviderResponseError
from src.ingestion.feed_sources import (
    FeedFormat,
    FeedSourceConfig,
    get_feed_source,
)
from src.ingestion.http_client import AsyncNewsHttpClient
from src.ingestion.providers.base import NewsProvider
from src.models import (
    Article,
    NewsSource,
    SourceType,
    current_utc_time,
)


HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


class RssFetchRequest(BaseModel):
    """Validated options for fetching an RSS or Atom feed."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    query: str = Field(
        default="",
        max_length=500,
    )

    max_records: int = Field(
        default=25,
        ge=1,
        le=200,
    )

    timespan: str = Field(
        default="7d",
        pattern=(
            r"^[1-9]\d*"
            r"(min|h|hours|d|days|w|weeks|m|months)$"
        ),
    )

    @field_validator("timespan")
    @classmethod
    def normalize_timespan(cls, value: str) -> str:
        """Normalize the timespan to lowercase."""

        return value.lower()


class HtmlTextExtractor(HTMLParser):
    """Convert basic HTML content into readable plain text."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._ignored_tag_depth = 0

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        """Ignore script and style content."""

        if tag.lower() in {"script", "style"}:
            self._ignored_tag_depth += 1

    def handle_endtag(self, tag: str) -> None:
        """Stop ignoring script and style content."""

        if (
            tag.lower() in {"script", "style"}
            and self._ignored_tag_depth > 0
        ):
            self._ignored_tag_depth -= 1

    def handle_data(self, data: str) -> None:
        """Store visible text from the HTML."""

        if self._ignored_tag_depth > 0:
            return

        cleaned_data = data.strip()

        if cleaned_data:
            self._parts.append(cleaned_data)

    def get_text(self) -> str:
        """Return the collected text."""

        return " ".join(self._parts)


def clean_html_text(value: str | None) -> str | None:
    """Remove HTML tags and normalize whitespace."""

    if not value:
        return None

    parser = HtmlTextExtractor()

    try:
        parser.feed(value)
        parser.close()
        cleaned_text = parser.get_text()
    except Exception:
        cleaned_text = value

    cleaned_text = html.unescape(cleaned_text)

    normalized_text = " ".join(
        cleaned_text.split()
    ).strip()

    return normalized_text or None


def timespan_to_timedelta(value: str) -> timedelta:
    """Convert a configured timespan into a timedelta."""

    normalized_value = value.strip().lower()

    suffixes = (
        "months",
        "month",
        "weeks",
        "week",
        "hours",
        "hour",
        "days",
        "day",
        "min",
        "h",
        "d",
        "w",
        "m",
    )

    suffix = next(
        (
            item
            for item in suffixes
            if normalized_value.endswith(item)
        ),
        None,
    )

    if suffix is None:
        raise ValueError(
            f"Unsupported timespan: {value}"
        )

    number_text = normalized_value[
        : -len(suffix)
    ]

    amount = int(number_text)

    if suffix == "min":
        return timedelta(minutes=amount)

    if suffix in {"h", "hour", "hours"}:
        return timedelta(hours=amount)

    if suffix in {"d", "day", "days"}:
        return timedelta(days=amount)

    if suffix in {"w", "week", "weeks"}:
        return timedelta(weeks=amount)

    if suffix in {"m", "month", "months"}:
        return timedelta(days=amount * 30)

    raise ValueError(
        f"Unsupported timespan: {value}"
    )


class RssNewsProvider(NewsProvider):
    """Collect articles from one configured RSS or Atom feed."""

    def __init__(
        self,
        feed_source: FeedSourceConfig | str,
        http_client: AsyncNewsHttpClient | None = None,
    ) -> None:
        if isinstance(feed_source, str):
            self._feed_source = get_feed_source(
                feed_source
            )
        else:
            self._feed_source = feed_source

        self._owns_http_client = http_client is None
        self._http_client = (
            http_client or AsyncNewsHttpClient()
        )

    @property
    def provider_name(self) -> str:
        """Return the configured source name."""

        return self._feed_source.name

    @property
    def feed_source(self) -> FeedSourceConfig:
        """Return the provider's feed configuration."""

        return self._feed_source

    async def __aenter__(self) -> "RssNewsProvider":
        """Enter the asynchronous context manager."""

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Close provider resources."""

        await self.close()

    async def close(self) -> None:
        """Close the internally created HTTP client."""

        if self._owns_http_client:
            await self._http_client.close()

    async def fetch_articles(
        self,
        query: str = "",
        max_records: int = 25,
        timespan: str = "7d",
    ) -> list[Article]:
        """Download, parse, filter, deduplicate, and validate entries."""

        request = RssFetchRequest(
            query=query,
            max_records=max_records,
            timespan=timespan,
        )

        effective_limit = min(
            request.max_records,
            self._feed_source.max_articles_per_fetch,
        )

        logger.info(
            "Fetching RSS feed source_id=%s "
            "source_name=%s max_records=%s timespan=%s",
            self._feed_source.source_id,
            self._feed_source.name,
            effective_limit,
            request.timespan,
        )

        response = await self._http_client.get_response(
            url=str(self._feed_source.feed_url)
        )

        parsed_feed = feedparser.parse(
            response.content
        )

        self._validate_parsed_feed(parsed_feed)

        cutoff_time = (
            current_utc_time()
            - timespan_to_timedelta(
                request.timespan
            )
        )

        articles: list[Article] = []
        seen_urls: set[str] = set()

        skipped_count = 0
        filtered_count = 0
        duplicate_count = 0

        for entry in parsed_feed.entries:
            if len(articles) >= effective_limit:
                break

            if not isinstance(entry, dict):
                skipped_count += 1
                continue

            try:
                article = self._map_entry(entry)
            except (
                KeyError,
                TypeError,
                ValueError,
                ValidationError,
            ) as exc:
                skipped_count += 1

                logger.warning(
                    "Skipping invalid feed entry "
                    "source_id=%s error=%s link=%s",
                    self._feed_source.source_id,
                    exc,
                    entry.get("link"),
                )

                continue

            normalized_url = str(article.url)

            if normalized_url in seen_urls:
                duplicate_count += 1

                logger.info(
                    "Skipping duplicate feed entry "
                    "source_id=%s url=%s",
                    self._feed_source.source_id,
                    normalized_url,
                )

                continue

            if article.published_at < cutoff_time:
                filtered_count += 1
                continue

            if not self._matches_query(
                article=article,
                query=request.query,
            ):
                filtered_count += 1
                continue

            seen_urls.add(normalized_url)
            articles.append(article)

        logger.info(
            "RSS ingestion completed "
            "source_id=%s received=%s "
            "validated=%s skipped=%s "
            "filtered=%s duplicates=%s",
            self._feed_source.source_id,
            len(parsed_feed.entries),
            len(articles),
            skipped_count,
            filtered_count,
            duplicate_count,
        )

        return articles

    def _validate_parsed_feed(
        self,
        parsed_feed: feedparser.FeedParserDict,
    ) -> None:
        """Validate feedparser's parsed result."""

        entries = parsed_feed.get(
            "entries",
            [],
        )

        if not isinstance(entries, list):
            raise NewsProviderResponseError(
                "The parsed feed entries field "
                "must be a list.",
                provider_name=self.provider_name,
                source_id=self._feed_source.source_id,
            )

        if parsed_feed.get("bozo"):
            parsing_error = parsed_feed.get(
                "bozo_exception"
            )

            logger.warning(
                "Feed parsing warning "
                "source_id=%s error=%s",
                self._feed_source.source_id,
                parsing_error,
            )

            if not entries:
                raise NewsProviderResponseError(
                    "The feed could not be parsed "
                    "and returned no entries: "
                    f"{parsing_error}",
                    provider_name=self.provider_name,
                    source_id=self._feed_source.source_id,
                )

        feed_version = str(
            parsed_feed.get("version", "")
        ).strip().lower()

        if not feed_version and not entries:
            raise NewsProviderResponseError(
                "RSS feed format could not be identified "
                "and the feed contains no entries.",
                provider_name=self.provider_name,
                source_id=self._feed_source.source_id,
            )

        if not feed_version:
            logger.warning(
                "Feed format could not be identified "
                "source_id=%s",
                self._feed_source.source_id,
            )

        self._check_expected_format(
            feed_version
        )

    def _check_expected_format(
        self,
        feed_version: str,
    ) -> None:
        """Log a warning when the feed format is unexpected."""

        expected_format = (
            self._feed_source.expected_format
        )

        if expected_format == FeedFormat.AUTO:
            return

        if (
            expected_format == FeedFormat.RSS
            and feed_version.startswith("atom")
        ):
            logger.warning(
                "Expected RSS but received Atom "
                "source_id=%s version=%s",
                self._feed_source.source_id,
                feed_version,
            )

        if (
            expected_format == FeedFormat.ATOM
            and feed_version.startswith("rss")
        ):
            logger.warning(
                "Expected Atom but received RSS "
                "source_id=%s version=%s",
                self._feed_source.source_id,
                feed_version,
            )

    def _map_entry(
        self,
        entry: dict[str, Any],
    ) -> Article:
        """Convert one parsed feed entry into an Article."""

        title = self._required_clean_text(
            entry=entry,
            field_name="title",
        )

        article_url = self._required_http_url(
            entry.get("link"),
            field_name="link",
        )

        description = self._extract_description(
            entry
        )

        content = self._extract_content(
            entry
        )

        published_at = self._extract_datetime(
            entry
        )

        source = NewsSource(
            name=self._feed_source.name,
            source_type=SourceType.RSS,
            homepage_url=(
                self._feed_source.homepage_url
            ),
            country_code=(
                self._feed_source.source_country_code
            ),
        )

        return Article(
            title=title[:500],
            description=(
                description[:2000]
                if description
                else None
            ),
            content=content,
            url=article_url,
            image_url=self._extract_image_url(
                entry
            ),
            source=source,
            author=self._extract_author(
                entry
            ),
            published_at=published_at,
            primary_category=(
                self._feed_source.default_category
            ),
            language_code=(
                self._feed_source.language_code
            ),
        )

    @staticmethod
    def _required_clean_text(
        entry: dict[str, Any],
        field_name: str,
    ) -> str:
        """Read and clean a required text field."""

        value = entry.get(field_name)

        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must be a string."
            )

        cleaned_value = clean_html_text(value)

        if not cleaned_value:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return cleaned_value

    @staticmethod
    def _required_http_url(
        value: Any,
        field_name: str,
    ) -> str:
        """Validate a required HTTP URL."""

        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must be a URL string."
            )

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        try:
            validated_url = (
                HTTP_URL_ADAPTER.validate_python(
                    cleaned_value
                )
            )
        except ValidationError as exc:
            raise ValueError(
                f"{field_name} is not a valid HTTP URL."
            ) from exc

        return str(validated_url)

    @staticmethod
    def _optional_http_url(
        value: Any,
    ) -> str | None:
        """Return a valid optional HTTP URL."""

        if not isinstance(value, str):
            return None

        cleaned_value = value.strip()

        if not cleaned_value:
            return None

        try:
            validated_url = (
                HTTP_URL_ADAPTER.validate_python(
                    cleaned_value
                )
            )
        except ValidationError:
            return None

        return str(validated_url)

    @staticmethod
    def _extract_description(
        entry: dict[str, Any],
    ) -> str | None:
        """Extract a plain-text description or summary."""

        possible_values = (
            entry.get("summary"),
            entry.get("description"),
            entry.get("subtitle"),
        )

        for value in possible_values:
            if isinstance(value, str):
                cleaned_value = clean_html_text(
                    value
                )

                if cleaned_value:
                    return cleaned_value

        return None

    @staticmethod
    def _extract_content(
        entry: dict[str, Any],
    ) -> str | None:
        """Extract the main article content from a feed entry."""

        content_items = entry.get("content")

        if isinstance(content_items, list):
            for content_item in content_items:
                if not isinstance(
                    content_item,
                    dict,
                ):
                    continue

                content_value = content_item.get(
                    "value"
                )

                if isinstance(content_value, str):
                    cleaned_content = clean_html_text(
                        content_value
                    )

                    if cleaned_content:
                        return cleaned_content

        return None

    @staticmethod
    def _extract_author(
        entry: dict[str, Any],
    ) -> str | None:
        """Extract the article author."""

        author = entry.get("author")

        if isinstance(author, str):
            cleaned_author = clean_html_text(
                author
            )

            if cleaned_author:
                return cleaned_author[:200]

        authors = entry.get("authors")

        if isinstance(authors, list):
            for author_item in authors:
                if not isinstance(
                    author_item,
                    dict,
                ):
                    continue

                name = author_item.get("name")

                if isinstance(name, str):
                    cleaned_name = clean_html_text(
                        name
                    )

                    if cleaned_name:
                        return cleaned_name[:200]

        return None

    @staticmethod
    def _extract_datetime(
        entry: dict[str, Any],
    ) -> datetime:
        """Extract and normalize the publication date."""

        parsed_date_fields = (
            "published_parsed",
            "updated_parsed",
            "created_parsed",
        )

        for field_name in parsed_date_fields:
            parsed_value = entry.get(
                field_name
            )

            if parsed_value:
                timestamp = calendar.timegm(
                    parsed_value
                )

                return datetime.fromtimestamp(
                    timestamp,
                    tz=timezone.utc,
                )

        text_date_fields = (
            "published",
            "updated",
            "created",
        )

        for field_name in text_date_fields:
            raw_value = entry.get(field_name)

            if not isinstance(raw_value, str):
                continue

            try:
                parsed_date = parsedate_to_datetime(
                    raw_value
                )
            except (TypeError, ValueError):
                try:
                    parsed_date = datetime.fromisoformat(
                        raw_value.replace(
                            "Z",
                            "+00:00",
                        )
                    )
                except ValueError:
                    continue

            if parsed_date.tzinfo is None:
                parsed_date = parsed_date.replace(
                    tzinfo=timezone.utc
                )

            return parsed_date.astimezone(
                timezone.utc
            )

        raise ValueError(
            "Feed entry does not contain "
            "a valid publication date."
        )

    def _extract_image_url(
        self,
        entry: dict[str, Any],
    ) -> str | None:
        """Extract an image URL from common RSS fields."""

        media_content = entry.get(
            "media_content"
        )

        if isinstance(media_content, list):
            for media_item in media_content:
                if not isinstance(
                    media_item,
                    dict,
                ):
                    continue

                media_type = str(
                    media_item.get("type", "")
                ).lower()

                medium = str(
                    media_item.get("medium", "")
                ).lower()

                if (
                    media_type
                    and not media_type.startswith(
                        "image/"
                    )
                    and medium != "image"
                ):
                    continue

                image_url = self._optional_http_url(
                    media_item.get("url")
                )

                if image_url:
                    return image_url

        media_thumbnail = entry.get(
            "media_thumbnail"
        )

        if isinstance(media_thumbnail, list):
            for thumbnail in media_thumbnail:
                if not isinstance(
                    thumbnail,
                    dict,
                ):
                    continue

                image_url = self._optional_http_url(
                    thumbnail.get("url")
                )

                if image_url:
                    return image_url

        enclosures = entry.get("enclosures")

        if isinstance(enclosures, list):
            for enclosure in enclosures:
                if not isinstance(
                    enclosure,
                    dict,
                ):
                    continue

                enclosure_type = str(
                    enclosure.get("type", "")
                ).lower()

                if (
                    enclosure_type
                    and not enclosure_type.startswith(
                        "image/"
                    )
                ):
                    continue

                image_url = self._optional_http_url(
                    enclosure.get("href")
                    or enclosure.get("url")
                )

                if image_url:
                    return image_url

        return None

    @staticmethod
    def _matches_query(
        article: Article,
        query: str,
    ) -> bool:
        """Apply an optional local text filter."""

        normalized_query = query.strip().casefold()

        if not normalized_query:
            return True

        searchable_text = " ".join(
            [
                article.title,
                article.description or "",
                article.content or "",
            ]
        ).casefold()

        return normalized_query in searchable_text