from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import boto3

from src.messaging.contracts import QueueMessageBase


MAX_SQS_DELAY_SECONDS = 900


class SqsClientProtocol(Protocol):
    """Minimal SQS client interface used by the publisher."""

    def send_message(self, **kwargs: Any) -> dict[str, Any]:
        """Send one message to Amazon SQS."""


class SqsPublisherError(RuntimeError):
    """Raised when a queue message cannot be published."""

    def __init__(self, *, queue_url: str, detail: str) -> None:
        self.queue_url = queue_url
        self.detail = detail
        super().__init__(
            "SQS message publishing failed "
            f"for queue={queue_url}: {detail}"
        )


@dataclass(frozen=True, slots=True)
class SqsSendResult:
    """Result returned after publishing one SQS message."""

    message_id: str
    md5_of_body: str | None = None
    sequence_number: str | None = None


class SqsMessagePublisher:
    """Publish validated application messages to Amazon SQS."""

    def __init__(
        self,
        *,
        queue_url: str,
        sqs_client: SqsClientProtocol | None = None,
    ) -> None:
        normalized_queue_url = queue_url.strip()

        if not normalized_queue_url:
            raise ValueError("queue_url cannot be empty.")

        self.queue_url = normalized_queue_url
        self.sqs_client = (
            sqs_client
            if sqs_client is not None
            else boto3.client("sqs")
        )

    @property
    def is_fifo_queue(self) -> bool:
        """Return whether the configured queue is FIFO."""

        return self.queue_url.lower().endswith(".fifo")

    def publish(
        self,
        *,
        message: QueueMessageBase,
        delay_seconds: int = 0,
        message_group_id: str | None = None,
        deduplication_id: str | None = None,
    ) -> SqsSendResult:
        """Publish one validated message to Amazon SQS."""

        if delay_seconds < 0 or delay_seconds > MAX_SQS_DELAY_SECONDS:
            raise ValueError(
                "delay_seconds must be between 0 and 900."
            )

        request: dict[str, Any] = {
            "QueueUrl": self.queue_url,
            "MessageBody": message.to_json(),
            "DelaySeconds": delay_seconds,
            "MessageAttributes": {
                "schema_version": {
                    "DataType": "String",
                    "StringValue": message.schema_version,
                },
                "message_type": {
                    "DataType": "String",
                    "StringValue": str(message.message_type),
                },
                "message_id": {
                    "DataType": "String",
                    "StringValue": str(message.message_id),
                },
            },
        }

        if self.is_fifo_queue:
            normalized_group_id = (
                message_group_id.strip()
                if message_group_id
                else ""
            )

            if not normalized_group_id:
                raise ValueError(
                    "message_group_id is required for FIFO queues."
                )

            request["MessageGroupId"] = normalized_group_id
            request["MessageDeduplicationId"] = (
                deduplication_id.strip()
                if deduplication_id
                else str(message.message_id)
            )
        elif message_group_id is not None or deduplication_id is not None:
            raise ValueError(
                "FIFO message options can only be used "
                "with a .fifo queue."
            )

        try:
            response = self.sqs_client.send_message(**request)
        except Exception as exc:
            raise SqsPublisherError(
                queue_url=self.queue_url,
                detail=str(exc),
            ) from exc

        message_id = str(response.get("MessageId", "")).strip()

        if not message_id:
            raise SqsPublisherError(
                queue_url=self.queue_url,
                detail="Amazon SQS returned no MessageId.",
            )

        md5_of_body = response.get("MD5OfMessageBody")
        sequence_number = response.get("SequenceNumber")

        return SqsSendResult(
            message_id=message_id,
            md5_of_body=(
                str(md5_of_body)
                if md5_of_body is not None
                else None
            ),
            sequence_number=(
                str(sequence_number)
                if sequence_number is not None
                else None
            ),
        )
