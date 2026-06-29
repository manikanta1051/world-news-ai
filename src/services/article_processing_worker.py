from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import ValidationError

from src.common.logging_config import logger
from src.messaging import ArticleProcessingMessage
from src.models import Article
from src.services.ingestion_exceptions import (
    ArticlePersistenceError,
)
from src.services.ingestion_persistence import (
    ArticlePersistenceResult,
    IngestionPersistenceService,
)


class ArticleProcessingWorkerError(RuntimeError):
    """Raised when an SQS article message cannot be processed."""

    def __init__(
        self,
        *,
        message_id: UUID | None,
        detail: str,
    ) -> None:
        self.message_id = message_id
        self.detail = detail

        message_identifier = (
            str(message_id)
            if message_id is not None
            else "unknown"
        )

        super().__init__(
            "Article processing worker failed "
            f"for message_id={message_identifier}: {detail}"
        )


@dataclass(frozen=True, slots=True)
class ArticleProcessingWorkerResult:
    """Result returned after processing one queue message."""

    message_id: UUID
    persistence_result: ArticlePersistenceResult


class ArticleProcessingWorker:
    """Convert SQS article messages into persisted articles."""

    def __init__(
        self,
        *,
        persistence_service: IngestionPersistenceService,
    ) -> None:
        self.persistence_service = persistence_service

    async def process_json(
        self,
        message_body: str | bytes,
    ) -> ArticleProcessingWorkerResult:
        """Validate and process one serialized SQS message."""

        try:
            message = ArticleProcessingMessage.from_json(
                message_body
            )
        except ValidationError as exc:
            raise ArticleProcessingWorkerError(
                message_id=None,
                detail=(
                    "Invalid ArticleProcessingMessage: "
                    f"{exc}"
                ),
            ) from exc

        return await self.process_message(
            message=message
        )

    async def process_message(
        self,
        *,
        message: ArticleProcessingMessage,
    ) -> ArticleProcessingWorkerResult:
        """Persist the article represented by one queue message."""

        try:
            article = Article.model_validate(
                message.article_payload
            )
        except ValidationError as exc:
            raise ArticleProcessingWorkerError(
                message_id=message.message_id,
                detail=(
                    "Invalid article payload: "
                    f"{exc}"
                ),
            ) from exc

        try:
            persistence_result = (
                await self.persistence_service
                .persist_article(
                    article=article,
                    raw_s3_uri=message.raw_s3_uri,
                    country_scores=(
                        message.country_scores
                    ),
                    state_scores=(
                        message.state_scores
                    ),
                    primary_state_code=(
                        message.primary_state_code
                    ),
                    state_detection_method=(
                        message.state_detection_method
                    ),
                )
            )
        except ArticlePersistenceError as exc:
            logger.exception(
                "Queued article persistence failed "
                "message_id=%s article_id=%s",
                message.message_id,
                article.article_id,
            )

            raise ArticleProcessingWorkerError(
                message_id=message.message_id,
                detail=str(exc),
            ) from exc

        logger.info(
            "Queued article processed "
            "message_id=%s article_id=%s status=%s",
            message.message_id,
            persistence_result.article_id,
            persistence_result.status,
        )

        return ArticleProcessingWorkerResult(
            message_id=message.message_id,
            persistence_result=persistence_result,
        )