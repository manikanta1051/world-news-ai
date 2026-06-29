from unittest.mock import AsyncMock, Mock

import pytest

from src.lambda_handlers import (
    ScheduledIngestionHandlerError,
    ScheduledIngestionLambdaHandler,
    SqsArticleLambdaHandler,
    SqsBatchEventError,
)
from src.messaging import (
    ScheduledIngestionMessage,
)
from src.services import (
    ArticleProcessingWorkerError,
    QueuedIngestionResult,
)


def create_scheduled_handler() -> tuple[
    ScheduledIngestionLambdaHandler,
    Mock,
    Mock,
]:
    """Create a scheduled handler with mocks."""

    dispatcher = Mock()
    dispatcher.dispatch = AsyncMock()

    provider = Mock()
    provider.provider_name = "GDELT"

    provider_resolver = Mock(
        return_value=provider
    )

    handler = ScheduledIngestionLambdaHandler(
        dispatcher=dispatcher,
        provider_resolver=provider_resolver,
    )

    return (
        handler,
        dispatcher,
        provider_resolver,
    )


@pytest.mark.asyncio
async def test_scheduled_handler_dispatches_event(
) -> None:
    """Confirm an EventBridge message is dispatched."""

    (
        handler,
        dispatcher,
        provider_resolver,
    ) = create_scheduled_handler()

    message = ScheduledIngestionMessage(
        provider="GDELT",
        query="India technology",
        max_records=20,
        timespan="24h",
        source_id="gdelt",
        extra_partitions={
            "environment": "test",
        },
    )

    dispatcher.dispatch.return_value = (
        QueuedIngestionResult(
            provider_name="GDELT",
            raw_s3_uri=(
                "s3://bucket/raw/gdelt/run.json"
            ),
            received_count=3,
            validated_count=2,
            queued_count=2,
            rejected_count=1,
            failed_count=0,
            sqs_message_ids=(
                "message-1",
                "message-2",
            ),
            rejected_s3_uris=(
                "s3://bucket/rejected/one.json",
            ),
            errors=(),
        )
    )

    response = await handler.handle(
        message.model_dump(mode="json")
    )

    provider_resolver.assert_called_once()

    dispatcher.dispatch.assert_awaited_once_with(
        provider=(
            provider_resolver.return_value
        ),
        query="India technology",
        max_records=20,
        timespan="24h",
        source_id="gdelt",
        raw_extra_partitions={
            "environment": "test",
        },
    )

    assert response["status"] == "completed"
    assert response["queued_count"] == 2
    assert response["rejected_count"] == 1
    assert response["failed_count"] == 0


@pytest.mark.asyncio
async def test_scheduled_handler_accepts_json(
) -> None:
    """Confirm a serialized event is accepted."""

    (
        handler,
        dispatcher,
        _,
    ) = create_scheduled_handler()

    message = ScheduledIngestionMessage(
        provider="GDELT",
        query="world news",
    )

    dispatcher.dispatch.return_value = (
        QueuedIngestionResult(
            provider_name="GDELT",
            raw_s3_uri="s3://bucket/raw/run.json",
            received_count=0,
            validated_count=0,
            queued_count=0,
            rejected_count=0,
            failed_count=0,
            sqs_message_ids=(),
            rejected_s3_uris=(),
            errors=(),
        )
    )

    response = await handler.handle(
        message.to_json()
    )

    assert response["provider"] == "GDELT"


@pytest.mark.asyncio
async def test_scheduled_handler_rejects_invalid_event(
) -> None:
    """Confirm invalid scheduler events are rejected."""

    handler, dispatcher, _ = (
        create_scheduled_handler()
    )

    with pytest.raises(
        ScheduledIngestionHandlerError,
        match=(
            "Invalid scheduled-ingestion event"
        ),
    ):
        await handler.handle(
            {
                "provider": "GDELT",
            }
        )

    dispatcher.dispatch.assert_not_awaited()


def create_sqs_handler() -> tuple[
    SqsArticleLambdaHandler,
    Mock,
]:
    """Create an SQS handler with a mocked worker."""

    worker = Mock()
    worker.process_json = AsyncMock()

    handler = SqsArticleLambdaHandler(
        worker=worker
    )

    return handler, worker


@pytest.mark.asyncio
async def test_sqs_handler_returns_no_failures(
) -> None:
    """Confirm successful records are acknowledged."""

    handler, worker = create_sqs_handler()

    response = await handler.handle(
        {
            "Records": [
                {
                    "messageId": "message-1",
                    "body": '{"value": 1}',
                },
                {
                    "messageId": "message-2",
                    "body": '{"value": 2}',
                },
            ]
        }
    )

    assert response == {
        "batchItemFailures": []
    }
    assert worker.process_json.await_count == 2


@pytest.mark.asyncio
async def test_sqs_handler_returns_partial_failure(
) -> None:
    """Confirm only failed records are retried."""

    handler, worker = create_sqs_handler()

    worker.process_json.side_effect = [
        None,
        ArticleProcessingWorkerError(
            message_id=None,
            detail="Database unavailable",
        ),
    ]

    response = await handler.handle(
        {
            "Records": [
                {
                    "messageId": "message-1",
                    "body": '{"value": 1}',
                },
                {
                    "messageId": "message-2",
                    "body": '{"value": 2}',
                },
            ]
        }
    )

    assert response == {
        "batchItemFailures": [
            {
                "itemIdentifier": (
                    "message-2"
                ),
            }
        ]
    }


@pytest.mark.asyncio
async def test_sqs_handler_marks_invalid_body_failed(
) -> None:
    """Confirm a non-string body is retried."""

    handler, worker = create_sqs_handler()

    response = await handler.handle(
        {
            "Records": [
                {
                    "messageId": "message-1",
                    "body": None,
                }
            ]
        }
    )

    assert response == {
        "batchItemFailures": [
            {
                "itemIdentifier": (
                    "message-1"
                ),
            }
        ]
    }
    worker.process_json.assert_not_awaited()


@pytest.mark.asyncio
async def test_sqs_handler_rejects_bad_top_level_event(
) -> None:
    """Confirm malformed SQS events are rejected."""

    handler, worker = create_sqs_handler()

    with pytest.raises(
        SqsBatchEventError,
        match="Records must be a sequence",
    ):
        await handler.handle({})

    worker.process_json.assert_not_awaited()
