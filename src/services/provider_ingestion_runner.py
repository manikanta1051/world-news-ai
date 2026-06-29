from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from src.common.logging_config import logger
from src.ingestion.provider_result import (
    ProviderFetchResult,
)
from src.models import Article
from src.services.batch_ingestion import (
    ArticleIngestionRequest,
    BatchIngestionCoordinator,
    BatchIngestionResult,
    RejectedIngestionItem,
)


class NewsProviderProtocol(Protocol):
    """Minimum interface required by the ingestion runner."""

    @property
    def provider_name(self) -> str:
        """Return the provider's readable name."""

    async def fetch_articles(
        self,
        query: str,
        max_records: int = 25,
        timespan: str = "24h",
    ) -> list[Article]:
        """Fetch and validate provider articles."""


class RawBatchNewsProviderProtocol(
    NewsProviderProtocol,
    Protocol,
):
    """Optional interface for providers exposing raw responses."""

    async def fetch_batch(
        self,
        query: str,
        max_records: int = 25,
        timespan: str = "24h",
    ) -> ProviderFetchResult:
        """Fetch raw data, validated articles, and rejections."""


ArticleRequestFactory = Callable[
    [Article],
    ArticleIngestionRequest,
]


@dataclass(frozen=True, slots=True)
class ProviderRunResult:
    """Result returned after one provider ingestion run."""

    provider_name: str
    fetched_count: int
    batch_result: BatchIngestionResult
    received_count: int = 0
    rejected_count: int = 0


def default_article_request_factory(
    article: Article,
) -> ArticleIngestionRequest:
    """Build persistence input from one validated article."""

    country_scores: dict[str, Decimal] = {}

    country_code = article.source.country_code

    if country_code:
        country_scores[
            country_code.strip().upper()
        ] = Decimal("1.0000")

    return ArticleIngestionRequest(
        article=article,
        country_scores=(
            country_scores or None
        ),
    )


class ProviderIngestionRunner:
    """Connect news providers to batch persistence."""

    def __init__(
        self,
        *,
        coordinator: BatchIngestionCoordinator,
    ) -> None:
        self.coordinator = coordinator

    async def run(
        self,
        *,
        provider: NewsProviderProtocol,
        query: str,
        max_records: int = 25,
        timespan: str = "24h",
        source_id: str | None = None,
        request_factory: ArticleRequestFactory | None = None,
        extra_partitions: Mapping[str, object] | None = None,
    ) -> ProviderRunResult:
        """Fetch, prepare, and persist one provider batch."""

        normalized_provider_name = (
            provider.provider_name.strip()
        )

        if not normalized_provider_name:
            raise ValueError(
                "Provider name cannot be empty."
            )

        if max_records < 1:
            raise ValueError(
                "max_records must be at least 1."
            )

        normalized_timespan = timespan.strip()

        if not normalized_timespan:
            raise ValueError(
                "timespan cannot be empty."
            )

        factory = (
            request_factory
            or default_article_request_factory
        )

        logger.info(
            "Provider ingestion starting "
            "provider=%s query=%s "
            "max_records=%s timespan=%s",
            normalized_provider_name,
            query,
            max_records,
            normalized_timespan,
        )

        fetch_result = (
            await self._fetch_provider_result(
                provider=provider,
                provider_name=normalized_provider_name,
                query=query,
                max_records=max_records,
                timespan=normalized_timespan,
            )
        )

        article_requests = tuple(
            factory(article)
            for article in fetch_result.articles
        )

        rejected_items = tuple(
            RejectedIngestionItem(
                payload=item.payload,
                reason=item.reason,
                source_id=item.source_id,
                extra_partitions=(
                    item.extra_partitions
                ),
            )
            for item in fetch_result.rejected_items
        )

        batch_result = (
            await self.coordinator.process_batch(
                provider=normalized_provider_name,
                raw_payload=fetch_result.raw_payload,
                article_requests=article_requests,
                rejected_items=rejected_items,
                source_id=source_id,
                query=query,
                raw_extra_partitions=(
                    extra_partitions
                ),
            )
        )

        logger.info(
            "Provider ingestion completed "
            "provider=%s received=%s fetched=%s "
            "rejected=%s stored=%s "
            "duplicates=%s failed=%s",
            normalized_provider_name,
            fetch_result.received_count,
            len(fetch_result.articles),
            len(fetch_result.rejected_items),
            batch_result.stored_count,
            batch_result.duplicate_count,
            batch_result.failed_count,
        )

        return ProviderRunResult(
            provider_name=normalized_provider_name,
            fetched_count=len(
                fetch_result.articles
            ),
            received_count=(
                fetch_result.received_count
            ),
            rejected_count=len(
                fetch_result.rejected_items
            ),
            batch_result=batch_result,
        )

    async def _fetch_provider_result(
        self,
        *,
        provider: NewsProviderProtocol,
        provider_name: str,
        query: str,
        max_records: int,
        timespan: str,
    ) -> ProviderFetchResult:
        """Use raw batch fetching when the provider supports it."""

        fetch_batch = getattr(
            provider,
            "fetch_batch",
            None,
        )

        if callable(fetch_batch):
            result = await fetch_batch(
                query=query,
                max_records=max_records,
                timespan=timespan,
            )

            if not isinstance(
                result,
                ProviderFetchResult,
            ):
                raise TypeError(
                    "fetch_batch must return "
                    "ProviderFetchResult."
                )

            return result

        articles = await provider.fetch_articles(
            query=query,
            max_records=max_records,
            timespan=timespan,
        )

        provider_snapshot = {
            "provider": provider_name,
            "query": query,
            "max_records": max_records,
            "timespan": timespan,
            "validated_count": len(articles),
            "validated_articles": [
                article.model_dump(mode="json")
                for article in articles
            ],
        }

        return ProviderFetchResult(
            provider_name=provider_name,
            raw_payload=provider_snapshot,
            articles=tuple(articles),
            received_count=len(articles),
        )
