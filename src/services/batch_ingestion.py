from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from src.common.logging_config import logger
from src.models import Article
from src.services.ingestion_exceptions import (
    ArticlePersistenceError,
    RejectedPayloadPersistenceError,
)
from src.services.ingestion_persistence import (
    ArticlePersistenceResult,
    IngestionPersistenceService,
    PersistenceStatus,
)

ScoreValue = Decimal | float | int


@dataclass(frozen=True, slots=True)
class ArticleIngestionRequest:
    """Persistence information for one validated article."""

    article: Article
    country_scores: Mapping[str, ScoreValue] | None = None
    state_scores: Mapping[str, ScoreValue] | None = None
    primary_state_code: str | None = None
    state_detection_method: str | None = None
    extra_partitions: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class RejectedIngestionItem:
    """One invalid provider record that must be stored."""

    payload: object
    reason: str
    source_id: str | None = None
    extra_partitions: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class BatchIngestionResult:
    """Summary returned after processing an ingestion batch."""

    provider: str
    raw_s3_uri: str
    total_received: int
    stored_count: int
    duplicate_count: int
    rejected_count: int
    failed_count: int
    article_results: tuple[ArticlePersistenceResult, ...]
    rejected_s3_uris: tuple[str, ...]
    errors: tuple[str, ...]


class BatchIngestionCoordinator:
    """Coordinate persistence for one provider batch."""

    def __init__(
        self,
        *,
        persistence_service: IngestionPersistenceService,
    ) -> None:
        self.persistence_service = persistence_service

    async def process_batch(
        self,
        *,
        provider: str,
        raw_payload: object,
        article_requests: Iterable[ArticleIngestionRequest],
        rejected_items: Iterable[RejectedIngestionItem] | None = None,
        source_id: str | None = None,
        query: str | None = None,
        raw_extra_partitions: Mapping[str, object] | None = None,
    ) -> BatchIngestionResult:
        """Store and process one complete provider response."""

        normalized_provider = provider.strip()

        if not normalized_provider:
            raise ValueError("Provider cannot be empty.")

        article_items = tuple(article_requests)
        rejected_records = tuple(rejected_items or ())

        raw_location = await self.persistence_service.store_raw_payload(
            provider=normalized_provider,
            payload=raw_payload,
            source_id=source_id,
            query=query,
            extra_partitions=raw_extra_partitions,
        )

        article_results: list[ArticlePersistenceResult] = []
        rejected_s3_uris: list[str] = []
        errors: list[str] = []

        for request in article_items:
            try:
                result = await self.persistence_service.persist_article(
                    article=request.article,
                    raw_s3_uri=raw_location.uri,
                    country_scores=request.country_scores,
                    state_scores=request.state_scores,
                    primary_state_code=request.primary_state_code,
                    state_detection_method=request.state_detection_method,
                    extra_partitions=request.extra_partitions,
                )
            except ArticlePersistenceError as exc:
                errors.append(str(exc))
                logger.warning(
                    "Batch article persistence failed provider=%s error=%s",
                    normalized_provider,
                    exc,
                )
                continue

            article_results.append(result)

        for rejected_item in rejected_records:
            try:
                rejected_location = (
                    await self.persistence_service.store_rejected_payload(
                        provider=normalized_provider,
                        payload=rejected_item.payload,
                        reason=rejected_item.reason,
                        source_id=rejected_item.source_id or source_id,
                        extra_partitions=rejected_item.extra_partitions,
                    )
                )
            except RejectedPayloadPersistenceError as exc:
                errors.append(str(exc))
                logger.warning(
                    "Batch rejected payload storage failed "
                    "provider=%s error=%s",
                    normalized_provider,
                    exc,
                )
                continue

            rejected_s3_uris.append(rejected_location.uri)

        stored_count = sum(
            result.status == PersistenceStatus.STORED
            for result in article_results
        )

        duplicate_count = sum(
            result.status == PersistenceStatus.DUPLICATE
            for result in article_results
        )

        batch_result = BatchIngestionResult(
            provider=normalized_provider,
            raw_s3_uri=raw_location.uri,
            total_received=len(article_items) + len(rejected_records),
            stored_count=stored_count,
            duplicate_count=duplicate_count,
            rejected_count=len(rejected_s3_uris),
            failed_count=len(errors),
            article_results=tuple(article_results),
            rejected_s3_uris=tuple(rejected_s3_uris),
            errors=tuple(errors),
        )

        logger.info(
            "Batch ingestion completed provider=%s total=%s stored=%s "
            "duplicates=%s rejected=%s failed=%s",
            batch_result.provider,
            batch_result.total_received,
            batch_result.stored_count,
            batch_result.duplicate_count,
            batch_result.rejected_count,
            batch_result.failed_count,
        )

        return batch_result
