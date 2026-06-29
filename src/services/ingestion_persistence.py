from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum, StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from src.common.logging_config import logger
from src.database.models import ArticleRecord
from src.database.repositories import (
    ArticleRepository,
    NewsSourceRepository,
)
from src.models import Article
from src.services.ingestion_exceptions import (
    ArticlePersistenceError,
    RawPayloadPersistenceError,
    RejectedPayloadPersistenceError,
)
from src.storage.s3_service import (
    S3NewsStorageService,
    S3ObjectLocation,
)


DEFAULT_RELEVANCE_SCORE = Decimal("1.0000")


class PersistenceStatus(StrEnum):
    """Possible article-persistence results."""

    STORED = "stored"
    DUPLICATE = "duplicate"


@dataclass(
    frozen=True,
    slots=True,
)
class ArticlePersistenceResult:
    """Result returned after processing one article."""

    status: PersistenceStatus
    article_id: UUID
    raw_s3_uri: str | None
    processed_s3_uri: str | None
    source_created: bool = False
    duplicate_reason: str | None = None


def enum_value(value: object) -> str:
    """Return a plain string from an enum or string value."""

    if isinstance(value, Enum):
        return str(value.value)

    return str(value)


def optional_url_string(
    value: object | None,
) -> str | None:
    """Convert an optional URL-like value into a string."""

    if value is None:
        return None

    text_value = str(value).strip()

    return text_value or None


def decimal_or_none(
    value: object | None,
) -> Decimal | None:
    """Convert an optional numeric value into Decimal."""

    if value is None:
        return None

    return Decimal(str(value))


def model_or_dictionary(
    value: object | None,
) -> dict[str, object]:
    """Convert supported metadata into a dictionary."""

    if value is None:
        return {}

    if isinstance(value, BaseModel):
        dumped_value = value.model_dump(
            mode="json"
        )

        if isinstance(dumped_value, dict):
            return dumped_value

        return {}

    if isinstance(value, dict):
        return dict(value)

    return {}


def normalize_relevance_scores(
    scores: Mapping[str, Decimal | float | int]
    | None,
) -> dict[str, Decimal]:
    """Validate location codes and relevance scores."""

    if scores is None:
        return {}

    normalized_scores: dict[str, Decimal] = {}

    for raw_code, raw_score in scores.items():
        code = raw_code.strip().upper()

        if not code:
            raise ValueError(
                "A relevance mapping code cannot be empty."
            )

        score = Decimal(str(raw_score))

        if score < 0 or score > 1:
            raise ValueError(
                "Relevance scores must be between "
                "0 and 1."
            )

        normalized_scores[code] = score

    return normalized_scores


class IngestionPersistenceService:
    """Coordinate Amazon S3 and PostgreSQL persistence."""

    def __init__(
        self,
        *,
        storage_service: S3NewsStorageService,
        source_repository: NewsSourceRepository,
        article_repository: ArticleRepository,
    ) -> None:
        self.storage_service = storage_service
        self.source_repository = source_repository
        self.article_repository = article_repository

    async def store_raw_payload(
        self,
        *,
        provider: str,
        payload: object,
        source_id: str | None = None,
        query: str | None = None,
        extra_partitions: Mapping[
            str,
            object,
        ]
        | None = None,
    ) -> S3ObjectLocation:
        """Store one original provider payload in S3."""

        try:
            location = (
                await self.storage_service
                .save_raw_payload(
                    provider=provider,
                    payload=payload,
                    source_id=source_id,
                    query=query,
                    extra_partitions=extra_partitions,
                )
            )
        except Exception as exc:
            logger.exception(
                "Raw ingestion payload storage failed "
                "provider=%s",
                provider,
            )

            raise RawPayloadPersistenceError(
                provider=provider,
                detail=str(exc),
            ) from exc

        logger.info(
            "Raw ingestion payload stored "
            "provider=%s uri=%s",
            provider,
            location.uri,
        )

        return location

    async def store_rejected_payload(
        self,
        *,
        provider: str,
        payload: object,
        reason: str,
        source_id: str | None = None,
        extra_partitions: Mapping[
            str,
            object,
        ]
        | None = None,
    ) -> S3ObjectLocation:
        """Store invalid provider data in the rejected layer."""

        try:
            location = (
                await self.storage_service
                .save_rejected_payload(
                    provider=provider,
                    payload=payload,
                    reason=reason,
                    source_id=source_id,
                    extra_partitions=extra_partitions,
                )
            )
        except Exception as exc:
            logger.exception(
                "Rejected ingestion payload storage failed "
                "provider=%s",
                provider,
            )

            raise RejectedPayloadPersistenceError(
                provider=provider,
                detail=str(exc),
            ) from exc

        logger.info(
            "Rejected ingestion payload stored "
            "provider=%s uri=%s",
            provider,
            location.uri,
        )

        return location

    async def persist_article(
        self,
        *,
        article: Article,
        raw_s3_uri: str | None = None,
        country_scores: Mapping[
            str,
            Decimal | float | int,
        ]
        | None = None,
        state_scores: Mapping[
            str,
            Decimal | float | int,
        ]
        | None = None,
        primary_state_code: str | None = None,
        state_detection_method: str | None = None,
        extra_partitions: Mapping[
            str,
            object,
        ]
        | None = None,
    ) -> ArticlePersistenceResult:
        """Persist one validated article."""

        article_url = str(article.url)

        try:
            duplicate_result = (
                await self._find_duplicate(
                    article
                )
            )

            if duplicate_result is not None:
                duplicate_article, reason = (
                    duplicate_result
                )

                logger.info(
                    "Skipping duplicate article "
                    "url=%s reason=%s existing_id=%s",
                    article_url,
                    reason,
                    duplicate_article.id,
                )

                return ArticlePersistenceResult(
                    status=(
                        PersistenceStatus.DUPLICATE
                    ),
                    article_id=duplicate_article.id,
                    raw_s3_uri=raw_s3_uri,
                    processed_s3_uri=(
                        duplicate_article
                        .processed_s3_uri
                    ),
                    duplicate_reason=reason,
                )

            source_record, source_created = (
                await self.source_repository
                .get_or_create(
                    name=article.source.name,
                    source_type=enum_value(
                        article.source.source_type
                    ),
                    homepage_url=optional_url_string(
                        article.source.homepage_url
                    ),
                    country_code=(
                        article.source.country_code
                    ),
                    credibility_score=decimal_or_none(
                        getattr(
                            article.source,
                            "credibility_score",
                            None,
                        )
                    ),
                )
            )

            processed_location = (
                await self.storage_service
                .save_article(
                    article=article,
                    extra_partitions=(
                        extra_partitions
                    ),
                )
            )

            article_record = self._build_article_record(
                article=article,
                source_id=source_record.id,
                raw_s3_uri=raw_s3_uri,
                processed_s3_uri=(
                    processed_location.uri
                ),
            )

            await self.article_repository.add(
                article_record
            )

            await self._persist_country_links(
                article=article,
                article_id=article_record.id,
                country_scores=country_scores,
            )

            await self._persist_state_links(
                article_id=article_record.id,
                state_scores=state_scores,
                primary_state_code=(
                    primary_state_code
                ),
                detection_method=(
                    state_detection_method
                ),
            )

        except Exception as exc:
            logger.exception(
                "Article persistence failed url=%s",
                article_url,
            )

            raise ArticlePersistenceError(
                article_url=article_url,
                detail=str(exc),
            ) from exc

        logger.info(
            "Article persisted "
            "article_id=%s url=%s processed_uri=%s",
            article_record.id,
            article_url,
            processed_location.uri,
        )

        return ArticlePersistenceResult(
            status=PersistenceStatus.STORED,
            article_id=article_record.id,
            raw_s3_uri=raw_s3_uri,
            processed_s3_uri=(
                processed_location.uri
            ),
            source_created=source_created,
        )

    async def _find_duplicate(
        self,
        article: Article,
    ) -> tuple[ArticleRecord, str] | None:
        """Find an existing article by URL or hash."""

        article_url = str(article.url)

        existing_by_url = (
            await self.article_repository
            .get_by_url(article_url)
        )

        if existing_by_url is not None:
            return existing_by_url, "url"

        content_hash = getattr(
            article,
            "content_hash",
            None,
        )

        if content_hash:
            existing_by_hash = (
                await self.article_repository
                .get_by_content_hash(
                    str(content_hash)
                )
            )

            if existing_by_hash is not None:
                return existing_by_hash, "content_hash"

        return None

    def _build_article_record(
        self,
        *,
        article: Article,
        source_id: UUID,
        raw_s3_uri: str | None,
        processed_s3_uri: str,
    ) -> ArticleRecord:
        """Convert the shared Article model into an ORM record."""

        social_card_data = model_or_dictionary(
            getattr(
                article,
                "social_card",
                None,
            )
        )

        keywords = list(
            getattr(
                article,
                "keywords",
                [],
            )
            or []
        )

        return ArticleRecord(
            id=article.article_id,
            source_id=source_id,
            title=article.title,
            description=article.description,
            content=article.content,
            summary=getattr(
                article,
                "summary",
                None,
            ),
            url=str(article.url),
            canonical_url=optional_url_string(
                getattr(
                    article,
                    "canonical_url",
                    None,
                )
            ),
            image_url=optional_url_string(
                article.image_url
            ),
            author=article.author,
            published_at=article.published_at,
            collected_at=getattr(
                article,
                "collected_at",
                article.published_at,
            ),
            primary_category=enum_value(
                article.primary_category
            ),
            sentiment=enum_value(
                getattr(
                    article,
                    "sentiment",
                    "Unknown",
                )
            ),
            language_code=article.language_code,
            ai_processed=bool(
                getattr(
                    article,
                    "ai_processed",
                    False,
                )
            ),
            content_hash=getattr(
                article,
                "content_hash",
                None,
            ),
            keywords=keywords,
            share_caption=getattr(
                article,
                "share_caption",
                None,
            ),
            social_card_data=social_card_data,
            raw_s3_uri=raw_s3_uri,
            processed_s3_uri=processed_s3_uri,
        )

    async def _persist_country_links(
        self,
        *,
        article: Article,
        article_id: UUID,
        country_scores: Mapping[
            str,
            Decimal | float | int,
        ]
        | None,
    ) -> None:
        """Store article-country relevance mappings."""

        normalized_scores = (
            normalize_relevance_scores(
                country_scores
            )
        )

        article_countries = getattr(
            article,
            "countries",
            [],
        )

        for country_code in article_countries:
            normalized_code = (
                str(country_code)
                .strip()
                .upper()
            )

            if normalized_code:
                normalized_scores.setdefault(
                    normalized_code,
                    DEFAULT_RELEVANCE_SCORE,
                )

        for country_code, relevance_score in (
            normalized_scores.items()
        ):
            await (
                self.article_repository
                .upsert_country_link(
                    article_id=article_id,
                    country_code=country_code,
                    relevance_score=(
                        relevance_score
                    ),
                )
            )

    async def _persist_state_links(
        self,
        *,
        article_id: UUID,
        state_scores: Mapping[
            str,
            Decimal | float | int,
        ]
        | None,
        primary_state_code: str | None,
        detection_method: str | None,
    ) -> None:
        """Store article-state relevance mappings."""

        normalized_scores = (
            normalize_relevance_scores(
                state_scores
            )
        )

        normalized_primary_state = (
            primary_state_code.strip().upper()
            if primary_state_code
            else None
        )

        if (
            normalized_primary_state is not None
            and normalized_primary_state
            not in normalized_scores
        ):
            raise ValueError(
                "The primary state must exist in "
                "state_scores."
            )

        for state_code, relevance_score in (
            normalized_scores.items()
        ):
            await (
                self.article_repository
                .upsert_state_link(
                    article_id=article_id,
                    state_code=state_code,
                    relevance_score=(
                        relevance_score
                    ),
                    is_primary=(
                        state_code
                        == normalized_primary_state
                    ),
                    detection_method=(
                        detection_method
                    ),
                )
            )