from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.messaging.contracts import (
    MAX_QUEUE_RETRY_COUNT,
    MESSAGE_SCHEMA_VERSION,
    ArticleProcessingMessage,
    QueueMessageType,
    ScheduledIngestionMessage,
)


def test_scheduled_ingestion_message_uses_defaults() -> None:
    message = ScheduledIngestionMessage(
        provider="gdelt",
        query="technology",
    )

    assert message.schema_version == MESSAGE_SCHEMA_VERSION
    assert message.message_type == QueueMessageType.INGESTION_TRIGGER
    assert message.provider == "gdelt"
    assert message.query == "technology"
    assert message.max_records == 25
    assert message.timespan == "24h"
    assert message.source_id is None
    assert message.extra_partitions == {}


def test_scheduled_ingestion_message_normalizes_timespan() -> None:
    message = ScheduledIngestionMessage(
        provider="rss",
        query="world news",
        timespan=" 12H ",
    )

    assert message.timespan == "12h"


def test_scheduled_ingestion_message_rejects_invalid_timespan() -> None:
    with pytest.raises(ValidationError):
        ScheduledIngestionMessage(
            provider="gdelt",
            query="technology",
            timespan="yesterday",
        )


def test_scheduled_ingestion_message_json_round_trip() -> None:
    original_message = ScheduledIngestionMessage(
        provider="gdelt",
        query="artificial intelligence",
        max_records=50,
        timespan="48h",
        source_id="gdelt-main",
        extra_partitions={
            "country": "US",
            "priority": 1,
        },
    )

    json_value = original_message.to_json()
    restored_message = ScheduledIngestionMessage.from_json(json_value)

    assert restored_message == original_message


def test_article_processing_message_normalizes_scores() -> None:
    message = ArticleProcessingMessage(
        provider="gdelt",
        raw_s3_uri="s3://world-news-raw/articles/article-1.json",
        article_payload={
            "title": "Example article",
            "url": "https://example.com/article-1",
        },
        country_scores={
            "us": 0.95,
            " in ": "0.75",
        },
        state_scores={
            "tx": 0.90,
        },
        primary_state_code=" tx ",
    )

    assert message.message_type == QueueMessageType.ARTICLE_PROCESSING
    assert message.country_scores == {
        "US": Decimal("0.95"),
        "IN": Decimal("0.75"),
    }
    assert message.state_scores == {
        "TX": Decimal("0.9"),
    }
    assert message.primary_state_code == "TX"
    assert message.retry_count == 0


@pytest.mark.parametrize(
    "raw_s3_uri",
    [
        "https://example.com/article.json",
        "s3://",
        "s3://bucket-only",
        "s3:///missing-bucket.json",
        "s3://bucket/",
    ],
)
def test_article_processing_message_rejects_invalid_s3_uri(
    raw_s3_uri: str,
) -> None:
    with pytest.raises(ValidationError):
        ArticleProcessingMessage(
            provider="gdelt",
            raw_s3_uri=raw_s3_uri,
            article_payload={
                "title": "Example article",
            },
        )


@pytest.mark.parametrize(
    "invalid_score",
    [
        -0.01,
        1.01,
        2,
    ],
)
def test_article_processing_message_rejects_invalid_scores(
    invalid_score: float,
) -> None:
    with pytest.raises(ValidationError):
        ArticleProcessingMessage(
            provider="gdelt",
            raw_s3_uri="s3://world-news-raw/article.json",
            article_payload={
                "title": "Example article",
            },
            country_scores={
                "US": invalid_score,
            },
        )


def test_primary_state_must_exist_in_state_scores() -> None:
    with pytest.raises(ValidationError):
        ArticleProcessingMessage(
            provider="gdelt",
            raw_s3_uri="s3://world-news-raw/article.json",
            article_payload={
                "title": "Example article",
            },
            state_scores={
                "CA": 0.8,
            },
            primary_state_code="TX",
        )


def test_retry_count_accepts_maximum_value() -> None:
    message = ArticleProcessingMessage(
        provider="rss",
        raw_s3_uri="s3://world-news-raw/article.json",
        article_payload={
            "title": "Example article",
        },
        retry_count=MAX_QUEUE_RETRY_COUNT,
    )

    assert message.retry_count == MAX_QUEUE_RETRY_COUNT


def test_retry_count_rejects_value_above_limit() -> None:
    with pytest.raises(ValidationError):
        ArticleProcessingMessage(
            provider="rss",
            raw_s3_uri="s3://world-news-raw/article.json",
            article_payload={
                "title": "Example article",
            },
            retry_count=MAX_QUEUE_RETRY_COUNT + 1,
        )


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        ScheduledIngestionMessage(
            provider="gdelt",
            query="technology",
            unknown_field="not-allowed",
        )