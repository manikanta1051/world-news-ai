from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from src.common.logging_config import logger
from src.ingestion.provider_result import ProviderFetchResult
from src.messaging import (
    ArticleProcessingMessage,
    SqsMessagePublisher,
    SqsPublisherError,
)
from src.models import Article
from src.services.ingestion_exceptions import (
    RejectedPayloadPersistenceError,
)


class RawBatchProviderProtocol(Protocol):
    """Provider interface required by queued ingestion."""

    @property
    def provider_name(self) -> str:
        """Return the provider's readable name."""

    async def fetch_batch(
        self,
        query: str,
        max_records: int = 25,
        timespan: str = "24h",
    ) -> ProviderFetchResult:
        """Return raw data, validated articles, and rejections."""


class RawPayloadStorageProtocol(Protocol):
    """Storage methods required by the dispatcher."""

    async def store_raw_payload(
        self,
        *,
        provider: str,
        payload: object,
        source_id: str | None = None,
        query: str | None = None,
        extra_partitions: Mapping[str, object] | None = None,
    ) -> object:
        """Store the original provider response."""

    async def store_rejected_payload(
        self,
        *,
        provider: str,
        payload: object,
        reason: str,
        source_id: str | None = None,
        extra_partitions: Mapping[str, object] | None = None,
    ) -> object:
        """Store one rejected provider record."""


ArticleMessageFactory = Callable[
    [Article, str, str],
    ArticleProcessingMessage,
]


@dataclass(frozen=True, slots=True)
class QueuedIngestionResult:
    """Summary returned after queueing one provider batch."""

    provider_name: str
    raw_s3_uri: str
    received_count: int
    validated_count: int
    queued_count: int
    rejected_count: int
    failed_count: int
    sqs_message_ids: tuple[str, ...]
    rejected_s3_uris: tuple[str, ...]
    errors: tuple[str, ...]


def default_article_message_factory(
    article: Article,
    provider_name: str,
    raw_s3_uri: str,
) -> ArticleProcessingMessage:
    """Build one SQS article-processing message."""

    country_scores: dict[str, Decimal] = {}

    country_code = article.source.country_code

    if country_code:
        country_scores[
            country_code.strip().upper()
        ] = Decimal("1.0000")

    return ArticleProcessingMessage(
        provider=provider_name,
        raw_s3_uri=raw_s3_uri,
        article_payload=article.model_dump(
            mode="json"
        ),
        country_scores=country_scores,
    )


class QueuedIngestionDispatcher:
    """Store a raw batch and queue validated articles."""

    def __init__(
        self,
        *,
        storage_service: RawPayloadStorageProtocol,
        publisher: SqsMessagePublisher,
    ) -> None:
        self.storage_service = storage_service
        self.publisher = publisher

    async def dispatch(
        self,
        *,
        provider: RawBatchProviderProtocol,
        query: str,
        max_records: int = 25,
        timespan: str = "24h",
        source_id: str | None = None,
        message_factory: ArticleMessageFactory | None = None,
        raw_extra_partitions: Mapping[str, object] | None = None,
    ) -> QueuedIngestionResult:
        """Fetch, store, and queue one provider batch."""

        provider_name = provider.provider_name.strip()

        if not provider_name:
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

        fetch_result = await provider.fetch_batch(
            query=query,
            max_records=max_records,
            timespan=normalized_timespan,
        )

        raw_location = (
            await self.storage_service
            .store_raw_payload(
                provider=provider_name,
                payload=fetch_result.raw_payload,
                source_id=source_id,
                query=query,
                extra_partitions=(
                    raw_extra_partitions
                ),
            )
        )

        raw_s3_uri = str(
            getattr(raw_location, "uri")
        )

        factory = (
            message_factory
            or default_article_message_factory
        )

        sqs_message_ids: list[str] = []
        rejected_s3_uris: list[str] = []
        errors: list[str] = []

        for article in fetch_result.articles:
            message = factory(
                article,
                provider_name,
                raw_s3_uri,
            )

            try:
                send_result = self.publisher.publish(
                    message=message
                )
            except SqsPublisherError as exc:
                errors.append(str(exc))

                logger.warning(
                    "Article queue publishing failed "
                    "provider=%s article_id=%s error=%s",
                    provider_name,
                    article.article_id,
                    exc,
                )
                continue

            sqs_message_ids.append(
                send_result.message_id
            )

        for rejected_item in (
            fetch_result.rejected_items
        ):
            try:
                rejected_location = (
                    await self.storage_service
                    .store_rejected_payload(
                        provider=provider_name,
                        payload=(
                            rejected_item.payload
                        ),
                        reason=(
                            rejected_item.reason
                        ),
                        source_id=(
                            rejected_item.source_id
                            or source_id
                        ),
                        extra_partitions=(
                            rejected_item
                            .extra_partitions
                        ),
                    )
                )
            except (
                RejectedPayloadPersistenceError
            ) as exc:
                errors.append(str(exc))

                logger.warning(
                    "Rejected record storage failed "
                    "provider=%s error=%s",
                    provider_name,
                    exc,
                )
                continue

            rejected_s3_uris.append(
                str(
                    getattr(
                        rejected_location,
                        "uri",
                    )
                )
            )

        result = QueuedIngestionResult(
            provider_name=provider_name,
            raw_s3_uri=raw_s3_uri,
            received_count=(
                fetch_result.received_count
            ),
            validated_count=len(
                fetch_result.articles
            ),
            queued_count=len(
                sqs_message_ids
            ),
            rejected_count=len(
                rejected_s3_uris
            ),
            failed_count=len(errors),
            sqs_message_ids=tuple(
                sqs_message_ids
            ),
            rejected_s3_uris=tuple(
                rejected_s3_uris
            ),
            errors=tuple(errors),
        )

        logger.info(
            "Queued ingestion completed "
            "provider=%s received=%s "
            "validated=%s queued=%s "
            "rejected=%s failed=%s",
            result.provider_name,
            result.received_count,
            result.validated_count,
            result.queued_count,
            result.rejected_count,
            result.failed_count,
        )

        return result
