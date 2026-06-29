from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from src.common.logging_config import logger
from src.services import (
    ArticleProcessingWorker,
    ArticleProcessingWorkerError,
)


class SqsBatchEventError(RuntimeError):
    """Raised when the top-level SQS event is malformed."""

    def __init__(
        self,
        *,
        detail: str,
    ) -> None:
        self.detail = detail

        super().__init__(
            "SQS batch event is invalid: "
            f"{detail}"
        )


@dataclass(
    frozen=True,
    slots=True,
)
class SqsBatchProcessingSummary:
    """Internal summary for one Lambda SQS batch."""

    total_count: int
    succeeded_count: int
    failed_message_ids: tuple[str, ...]

    def to_lambda_response(
        self,
    ) -> dict[str, list[dict[str, str]]]:
        """Return the AWS partial-batch response."""

        return {
            "batchItemFailures": [
                {
                    "itemIdentifier": (
                        message_id
                    ),
                }
                for message_id
                in self.failed_message_ids
            ]
        }


class SqsArticleLambdaHandler:
    """Handle SQS article messages with partial failures."""

    def __init__(
        self,
        *,
        worker: ArticleProcessingWorker,
    ) -> None:
        self.worker = worker

    async def handle(
        self,
        event: Mapping[str, Any],
    ) -> dict[str, list[dict[str, str]]]:
        """Process an SQS event and return partial failures."""

        summary = await self.process_event(
            event
        )

        return summary.to_lambda_response()

    async def process_event(
        self,
        event: Mapping[str, Any],
    ) -> SqsBatchProcessingSummary:
        """Process every record in one SQS Lambda event."""

        records = event.get("Records")

        if not isinstance(records, Sequence):
            raise SqsBatchEventError(
                detail=(
                    "Records must be a sequence."
                ),
            )

        failed_message_ids: list[str] = []
        succeeded_count = 0

        for index, record in enumerate(records):
            if not isinstance(record, Mapping):
                raise SqsBatchEventError(
                    detail=(
                        "Each Records entry must "
                        "be an object."
                    ),
                )

            message_id = self._message_id(
                record=record,
                index=index,
            )

            body = record.get("body")

            if not isinstance(body, str):
                failed_message_ids.append(
                    message_id
                )

                logger.warning(
                    "SQS record body is invalid "
                    "message_id=%s",
                    message_id,
                )
                continue

            try:
                await self.worker.process_json(
                    body
                )
            except (
                ArticleProcessingWorkerError
            ) as exc:
                failed_message_ids.append(
                    message_id
                )

                logger.warning(
                    "SQS article processing failed "
                    "message_id=%s error=%s",
                    message_id,
                    exc,
                )
                continue
            except Exception as exc:
                failed_message_ids.append(
                    message_id
                )

                logger.exception(
                    "Unexpected SQS processing failure "
                    "message_id=%s error=%s",
                    message_id,
                    exc,
                )
                continue

            succeeded_count += 1

        summary = SqsBatchProcessingSummary(
            total_count=len(records),
            succeeded_count=succeeded_count,
            failed_message_ids=tuple(
                failed_message_ids
            ),
        )

        logger.info(
            "SQS batch processing completed "
            "total=%s succeeded=%s failed=%s",
            summary.total_count,
            summary.succeeded_count,
            len(summary.failed_message_ids),
        )

        return summary

    @staticmethod
    def _message_id(
        *,
        record: Mapping[str, Any],
        index: int,
    ) -> str:
        """Read the SQS message identifier."""

        raw_message_id = record.get(
            "messageId"
        )

        if not isinstance(
            raw_message_id,
            str,
        ):
            raise SqsBatchEventError(
                detail=(
                    "Record at index "
                    f"{index} has no messageId."
                ),
            )

        message_id = raw_message_id.strip()

        if not message_id:
            raise SqsBatchEventError(
                detail=(
                    "Record at index "
                    f"{index} has an empty messageId."
                ),
            )

        return message_id
