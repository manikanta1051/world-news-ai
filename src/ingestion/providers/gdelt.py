from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import pycountry
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    TypeAdapter,
    ValidationError,
    field_validator,
)

from src.common.config import settings
from src.common.logging_config import logger
from src.ingestion.exceptions import (
    NewsProviderResponseError,
)
from src.ingestion.http_client import (
    AsyncNewsHttpClient,
    JsonResponse,
)
from src.ingestion.provider_result import (
    ProviderFetchResult,
    ProviderRejectedItem,
)
from src.ingestion.providers.base import NewsProvider
from src.models import (
    Article,
    NewsCategory,
    NewsSource,
    SourceType,
)


HTTP_URL_ADAPTER = TypeAdapter(HttpUrl)


class GdeltSearchRequest(BaseModel):
    """Validated search options for the GDELT DOC API."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )

    query: str = Field(
        min_length=3,
        max_length=1000,
    )

    max_records: int = Field(
        default=25,
        ge=1,
        le=250,
    )

    timespan: str = Field(
        default="24h",
        pattern=(
            r"^[1-9]\d*"
            r"(min|h|hours|d|days|w|weeks|m|months)$"
        ),
    )

    @field_validator(
        "timespan",
        mode="before",
    )
    @classmethod
    def normalize_timespan(
        cls,
        value: object,
    ) -> object:
        """Normalize timespan text before pattern validation."""

        if isinstance(value, str):
            return value.strip().lower()

        return value

    @field_validator("timespan")
    @classmethod
    def validate_timespan(cls, value: str) -> str:
        """Ensure minute searches cover at least 15 minutes."""

        if value.endswith("min"):
            minute_value = int(
                value.removesuffix("min")
            )

            if minute_value < 15:
                raise ValueError(
                    "GDELT minute timespan must be "
                    "at least 15 minutes."
                )

        return value


class GdeltNewsProvider(NewsProvider):
    """Collect and validate articles from GDELT."""

    def __init__(
        self,
        http_client: AsyncNewsHttpClient | None = None,
    ) -> None:
        self._owns_http_client = http_client is None
        self._http_client = (
            http_client or AsyncNewsHttpClient()
        )

    @property
    def provider_name(self) -> str:
        """Return the readable provider name."""

        return "GDELT"

    async def __aenter__(self) -> "GdeltNewsProvider":
        """Enter the asynchronous context manager."""

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Close resources when leaving the context."""

        await self.close()

    async def close(self) -> None:
        """Close the internally created HTTP client."""

        if self._owns_http_client:
            await self._http_client.close()

    async def fetch_articles(
        self,
        query: str,
        max_records: int = 25,
        timespan: str = "24h",
    ) -> list[Article]:
        """Fetch only validated GDELT articles."""

        batch_result = await self.fetch_batch(
            query=query,
            max_records=max_records,
            timespan=timespan,
        )

        return list(batch_result.articles)

    async def fetch_batch(
        self,
        query: str,
        max_records: int = 25,
        timespan: str = "24h",
    ) -> ProviderFetchResult:
        """Fetch the raw response, valid articles, and rejections."""

        request = GdeltSearchRequest(
            query=query,
            max_records=max_records,
            timespan=timespan,
        )

        logger.info(
            "Fetching GDELT batch query=%s "
            "max_records=%s timespan=%s",
            request.query,
            request.max_records,
            request.timespan,
        )

        response_data = await self._http_client.get_json(
            url=settings.gdelt_base_url,
            params=self._build_request_params(request),
        )

        raw_articles = self._extract_raw_articles(
            response_data
        )

        articles: list[Article] = []
        rejected_items: list[
            ProviderRejectedItem
        ] = []

        for raw_article in raw_articles:
            if not isinstance(raw_article, dict):
                rejected_items.append(
                    ProviderRejectedItem(
                        payload=raw_article,
                        reason=(
                            "GDELT article must be "
                            "an object."
                        ),
                    )
                )

                logger.warning(
                    "Rejecting non-object GDELT result "
                    "value_type=%s",
                    type(raw_article).__name__,
                )

                continue

            try:
                article = self._map_article(
                    raw_article
                )
            except (
                KeyError,
                TypeError,
                ValueError,
                ValidationError,
            ) as exc:
                rejected_items.append(
                    ProviderRejectedItem(
                        payload=raw_article,
                        reason=str(exc),
                        source_id=self._source_id(
                            raw_article
                        ),
                    )
                )

                logger.warning(
                    "Rejecting invalid GDELT article "
                    "error=%s raw_url=%s",
                    exc,
                    raw_article.get("url"),
                )

                continue

            articles.append(article)

        logger.info(
            "GDELT batch completed "
            "received=%s validated=%s rejected=%s",
            len(raw_articles),
            len(articles),
            len(rejected_items),
        )

        return ProviderFetchResult(
            provider_name=self.provider_name,
            raw_payload=response_data,
            articles=tuple(articles),
            received_count=len(raw_articles),
            rejected_items=tuple(rejected_items),
        )

    @staticmethod
    def _build_request_params(
        request: GdeltSearchRequest,
    ) -> dict[str, str | int]:
        """Build the GDELT DOC API query parameters."""

        return {
            "query": request.query,
            "mode": "artlist",
            "maxrecords": request.max_records,
            "timespan": request.timespan,
            "sort": "datedesc",
            "format": "json",
        }

    def _extract_raw_articles(
        self,
        response_data: JsonResponse,
    ) -> list[Any]:
        """Extract all raw article values without discarding them."""

        if not isinstance(response_data, dict):
            raise NewsProviderResponseError(
                provider_name=self.provider_name,
                detail=(
                    "Top-level JSON must be an object."
                ),
            )

        raw_articles = response_data.get("articles")

        if raw_articles is None:
            raise NewsProviderResponseError(
                provider_name=self.provider_name,
                detail=(
                    "The articles field is missing."
                ),
            )

        if not isinstance(raw_articles, list):
            raise NewsProviderResponseError(
                provider_name=self.provider_name,
                detail=(
                    "The articles field must be a list."
                ),
            )

        return raw_articles

    def _map_article(
        self,
        raw_article: dict[str, Any],
    ) -> Article:
        """Convert one GDELT result into an Article model."""

        article_url = self._required_text(
            raw_article,
            "url",
        )

        article_title = self._required_text(
            raw_article,
            "title",
        )

        seen_date = self._required_text(
            raw_article,
            "seendate",
        )

        domain = self._get_domain(
            raw_article=raw_article,
            article_url=article_url,
        )

        source_country_code = (
            self._country_name_to_code(
                raw_article.get(
                    "sourcecountry"
                )
            )
        )

        source = NewsSource(
            name=domain,
            source_type=SourceType.GDELT,
            homepage_url=(
                self._build_homepage_url(
                    article_url
                )
            ),
            country_code=source_country_code,
        )

        return Article(
            title=article_title,
            url=article_url,
            image_url=self._optional_http_url(
                raw_article.get("socialimage")
            ),
            source=source,
            published_at=(
                self._parse_gdelt_datetime(
                    seen_date
                )
            ),
            primary_category=(
                NewsCategory.GENERAL
            ),
            language_code=(
                self._language_to_code(
                    raw_article.get("language")
                )
            ),
        )

    @staticmethod
    def _source_id(
        raw_article: dict[str, Any],
    ) -> str | None:
        """Return a stable provider identifier when available."""

        raw_url = raw_article.get("url")

        if isinstance(raw_url, str):
            normalized_url = raw_url.strip()

            if normalized_url:
                return normalized_url

        return None

    @staticmethod
    def _required_text(
        raw_article: dict[str, Any],
        field_name: str,
    ) -> str:
        """Read a required non-empty text value."""

        value = raw_article.get(field_name)

        if not isinstance(value, str):
            raise ValueError(
                f"{field_name} must be a string."
            )

        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(
                f"{field_name} cannot be empty."
            )

        return cleaned_value

    @staticmethod
    def _get_domain(
        raw_article: dict[str, Any],
        article_url: str,
    ) -> str:
        """Return the source domain for an article."""

        domain = raw_article.get("domain")

        if (
            isinstance(domain, str)
            and domain.strip()
        ):
            return domain.strip().lower()

        parsed_url = urlparse(article_url)

        if parsed_url.netloc:
            return parsed_url.netloc.lower()

        raise ValueError(
            "The article source domain is missing."
        )

    @staticmethod
    def _build_homepage_url(
        article_url: str,
    ) -> str | None:
        """Build the publisher homepage from the article URL."""

        parsed_url = urlparse(article_url)

        if (
            not parsed_url.scheme
            or not parsed_url.netloc
        ):
            return None

        return (
            f"{parsed_url.scheme}://"
            f"{parsed_url.netloc}"
        )

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
                HTTP_URL_ADAPTER
                .validate_python(
                    cleaned_value
                )
            )
        except ValidationError:
            logger.warning(
                "Ignoring invalid optional "
                "image URL url=%s",
                cleaned_value,
            )
            return None

        return str(validated_url)

    @staticmethod
    def _parse_gdelt_datetime(
        value: str,
    ) -> datetime:
        """Convert a GDELT date into a UTC datetime."""

        supported_formats = (
            "%Y%m%dT%H%M%SZ",
            "%Y%m%d%H%M%S",
            "%Y-%m-%dT%H:%M:%SZ",
        )

        for date_format in supported_formats:
            try:
                parsed_date = datetime.strptime(
                    value,
                    date_format,
                )

                return parsed_date.replace(
                    tzinfo=timezone.utc
                )
            except ValueError:
                continue

        try:
            parsed_date = (
                datetime.fromisoformat(
                    value.replace(
                        "Z",
                        "+00:00",
                    )
                )
            )
        except ValueError as exc:
            raise ValueError(
                "Unsupported GDELT date "
                f"format: {value}"
            ) from exc

        if parsed_date.tzinfo is None:
            parsed_date = parsed_date.replace(
                tzinfo=timezone.utc
            )

        return parsed_date.astimezone(
            timezone.utc
        )

    @staticmethod
    def _country_name_to_code(
        value: Any,
    ) -> str | None:
        """Convert a source-country name to an ISO code."""

        if not isinstance(value, str):
            return None

        cleaned_value = value.strip()

        if not cleaned_value:
            return None

        try:
            country = pycountry.countries.lookup(
                cleaned_value
            )
        except LookupError:
            logger.warning(
                "Unable to map GDELT source "
                "country country=%s",
                cleaned_value,
            )
            return None

        return country.alpha_2

    @staticmethod
    def _language_to_code(
        value: Any,
    ) -> str:
        """Convert a language name into an ISO language code."""

        if not isinstance(value, str):
            return "und"

        cleaned_value = value.strip()

        if not cleaned_value:
            return "und"

        try:
            language = (
                pycountry.languages.lookup(
                    cleaned_value
                )
            )
        except LookupError:
            logger.warning(
                "Unable to map GDELT language "
                "language=%s",
                cleaned_value,
            )
            return "und"

        alpha_2 = getattr(
            language,
            "alpha_2",
            None,
        )

        if alpha_2:
            return str(alpha_2).lower()

        alpha_3 = getattr(
            language,
            "alpha_3",
            "und",
        )

        return str(alpha_3).lower()
