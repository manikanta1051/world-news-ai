from unittest.mock import Mock

import pytest

from src.messaging import (
    ArticleProcessingMessage,
    ScheduledIngestionMessage,
    SqsMessagePublisher,
    SqsPublisherError,
)


def create_scheduled_message() -> ScheduledIngestionMessage:
    """Create one valid scheduled-ingestion message."""

    return ScheduledIngestionMessage(
        provider="GDELT",
        query="India technology",
        max_records=20,
        timespan="24h",
    )


def test_standard_queue_message_is_published() -> None:
    """Confirm a standard SQS message is sent correctly."""

    sqs_client = Mock()
    sqs_client.send_message.return_value = {
        "MessageId": "message-123",
        "MD5OfMessageBody": "abc123",
    }

    publisher = SqsMessagePublisher(
        queue_url=(
            "https://sqs.us-east-1.amazonaws.com/"
            "123456789012/world-news-processing"
        ),
        sqs_client=sqs_client,
    )

    message = create_scheduled_message()

    result = publisher.publish(
        message=message,
        delay_seconds=10,
    )

    assert result.message_id == "message-123"
    assert result.md5_of_body == "abc123"
    assert result.sequence_number is None

    sqs_client.send_message.assert_called_once()

    request = sqs_client.send_message.call_args.kwargs

    assert request["QueueUrl"] == (
        "https://sqs.us-east-1.amazonaws.com/"
        "123456789012/world-news-processing"
    )
    assert request["DelaySeconds"] == 10
    assert "MessageGroupId" not in request
    assert "MessageDeduplicationId" not in request

    restored = ScheduledIngestionMessage.from_json(
        request["MessageBody"]
    )

    assert restored == message


def test_fifo_queue_requires_group_id() -> None:
    """Confirm FIFO queues require a message group."""

    publisher = SqsMessagePublisher(
        queue_url=(
            "https://sqs.us-east-1.amazonaws.com/"
            "123456789012/world-news.fifo"
        ),
        sqs_client=Mock(),
    )

    with pytest.raises(
        ValueError,
        match="message_group_id is required",
    ):
        publisher.publish(
            message=create_scheduled_message()
        )


def test_fifo_message_uses_message_id_for_deduplication() -> None:
    """Confirm FIFO deduplication defaults to message_id."""

    sqs_client = Mock()
    sqs_client.send_message.return_value = {
        "MessageId": "fifo-message-1",
        "SequenceNumber": "1001",
    }

    publisher = SqsMessagePublisher(
        queue_url=(
            "https://sqs.us-east-1.amazonaws.com/"
            "123456789012/world-news.fifo"
        ),
        sqs_client=sqs_client,
    )

    message = ArticleProcessingMessage(
        provider="GDELT",
        raw_s3_uri=(
            "s3://world-news-bucket/"
            "raw/gdelt/response.json"
        ),
        article_payload={
            "title": "India technology update",
        },
    )

    result = publisher.publish(
        message=message,
        message_group_id="gdelt",
    )

    assert result.message_id == "fifo-message-1"
    assert result.sequence_number == "1001"

    request = sqs_client.send_message.call_args.kwargs

    assert request["MessageGroupId"] == "gdelt"
    assert request["MessageDeduplicationId"] == (
        str(message.message_id)
    )


def test_fifo_options_are_rejected_for_standard_queue() -> None:
    """Confirm FIFO-only options are blocked."""

    publisher = SqsMessagePublisher(
        queue_url=(
            "https://sqs.us-east-1.amazonaws.com/"
            "123456789012/world-news"
        ),
        sqs_client=Mock(),
    )

    with pytest.raises(
        ValueError,
        match="FIFO message options",
    ):
        publisher.publish(
            message=create_scheduled_message(),
            message_group_id="gdelt",
        )


def test_delay_seconds_are_validated() -> None:
    """Confirm SQS delay remains within supported limits."""

    publisher = SqsMessagePublisher(
        queue_url=(
            "https://sqs.us-east-1.amazonaws.com/"
            "123456789012/world-news"
        ),
        sqs_client=Mock(),
    )

    with pytest.raises(
        ValueError,
        match="between 0 and 900",
    ):
        publisher.publish(
            message=create_scheduled_message(),
            delay_seconds=901,
        )


def test_client_failure_is_converted() -> None:
    """Confirm client failures use a clear error."""

    sqs_client = Mock()
    sqs_client.send_message.side_effect = (
        RuntimeError("SQS unavailable")
    )

    publisher = SqsMessagePublisher(
        queue_url=(
            "https://sqs.us-east-1.amazonaws.com/"
            "123456789012/world-news"
        ),
        sqs_client=sqs_client,
    )

    with pytest.raises(
        SqsPublisherError,
        match="SQS unavailable",
    ):
        publisher.publish(
            message=create_scheduled_message()
        )


def test_missing_message_id_is_rejected() -> None:
    """Confirm incomplete SQS responses are rejected."""

    sqs_client = Mock()
    sqs_client.send_message.return_value = {
        "MD5OfMessageBody": "abc123",
    }

    publisher = SqsMessagePublisher(
        queue_url=(
            "https://sqs.us-east-1.amazonaws.com/"
            "123456789012/world-news"
        ),
        sqs_client=sqs_client,
    )

    with pytest.raises(
        SqsPublisherError,
        match="returned no MessageId",
    ):
        publisher.publish(
            message=create_scheduled_message()
        )
