from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from pydantic import ValidationError

from src.common.logging_config import logger
from src.messaging import ScheduledIngestionMessage
from src.services import (
    QueuedIngestionDispatcher,
    RawBatchProviderProtocol,
)


ProviderResolver = Callable[
    [ScheduledIngestionMessage],
    RawBatchProviderProtocol,
]


class ScheduledIngestionHandlerError(RuntimeError):
    """Raised when a scheduled-ingestion event cannot be handled."""

    def __init__(
        self,
        *,
        detail: str,
    ) -> None:
        self.detail = detail

        super().__init__(
            "Scheduled ingestion handler failed: "
            f"{detail}"
        )


class ScheduledIngestionLambdaHandler:
    """Handle one EventBridge scheduled-ingestion event."""

    def __init__(
        self,
        *,
        dispatcher: QueuedIngestionDispatcher,
        provider_resolver: ProviderResolver,
    ) -> None:
        self.dispatcher = dispatcher
        self.provider_resolver = provider_resolver

    async def handle(
        self,
        event: Mapping[str, Any] | str | bytes,
    ) -> dict[str, Any]:
        """Validate an event and dispatch one provider batch."""

        message = self._parse_message(event)

        try:
            provider = self.provider_resolver(
                message
            )
        except Exception as exc:
            raise ScheduledIngestionHandlerError(
                detail=(
                    "Provider resolution failed for "
                    f"provider={message.provider}: {exc}"
                ),
            ) from exc

        try:
            result = await self.dispatcher.dispatch(
                provider=provider,
                query=message.query,
                max_records=message.max_records,
                timespan=message.timespan,
                source_id=message.source_id,
                raw_extra_partitions=(
                    message.extra_partitions
                ),
            )
        except Exception as exc:
            logger.exception(
                "Scheduled ingestion dispatch failed "
                "message_id=%s provider=%s",
                message.message_id,
                message.provider,
            )

            raise ScheduledIngestionHandlerError(
                detail=str(exc),
            ) from exc

        logger.info(
            "Scheduled ingestion event completed "
            "message_id=%s provider=%s "
            "received=%s queued=%s rejected=%s "
            "failed=%s",
            message.message_id,
            result.provider_name,
            result.received_count,
            result.queued_count,
            result.rejected_count,
            result.failed_count,
        )

        return {
            "status": "completed",
            "message_id": str(
                message.message_id
            ),
            "provider": result.provider_name,
            "raw_s3_uri": result.raw_s3_uri,
            "received_count": (
                result.received_count
            ),
            "validated_count": (
                result.validated_count
            ),
            "queued_count": (
                result.queued_count
            ),
            "rejected_count": (
                result.rejected_count
            ),
            "failed_count": (
                result.failed_count
            ),
        }

    @staticmethod
    def _parse_message(
        event: Mapping[str, Any] | str | bytes,
    ) -> ScheduledIngestionMessage:
        """Convert an EventBridge payload into a message."""

        try:
            if isinstance(
                event,
                (str, bytes),
            ):
                return (
                    ScheduledIngestionMessage
                    .from_json(event)
                )

            return (
                ScheduledIngestionMessage
                .model_validate(dict(event))
            )
        except (
            ValidationError,
            TypeError,
            ValueError,
        ) as exc:
            raise ScheduledIngestionHandlerError(
                detail=(
                    "Invalid scheduled-ingestion event: "
                    f"{exc}"
                ),
            ) from exc
