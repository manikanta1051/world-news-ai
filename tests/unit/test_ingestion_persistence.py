from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import (
    AsyncMock,
    Mock,
)
from uuid import uuid4

import pytest

from src.database.models import (
    ArticleRecord,
    NewsSourceRecord,
)
from src.database.repositories import (
    ArticleRepository,
    NewsSourceRepository,
)
from src.models import (
    Article,
    NewsCategory,
    NewsSource,
    SourceType,
)
from src.services import (
    ArticlePersistenceError,
    IngestionPersistenceService,
    PersistenceStatus,
    RawPayloadPersistenceError,
    normalize_relevance_scores,
)
from src.storage.s3_service import (
    S3NewsStorageService,
    S3ObjectLocation,
)


def create_article() -> Article:
    """Create a validated article for tests."""

    return Article(
        article_id=uuid4(),
        title="Telangana technology development",
        description="Technology news from Telangana.",
        content="Detailed technology article content.",
        url="https://example.com/telangana-technology",
        image_url="https://example.com/image.jpg",
        source=NewsSource(
            name="Example News",
            source_type=SourceType.RSS,
            homepage_url="https://example.com",
            country_code="IN",
        ),
        author="Example Author",
        published_at=datetime(
            2026,
            6,
            27,
            12,
            0,
            tzinfo=timezone.utc,
        ),
        primary_category=NewsCategory.GENERAL,
        language_code="en",
        content_hash="a" * 64,
    )


def create_service() -> tuple[
    IngestionPersistenceService,
    Mock,
    Mock,
    Mock,
]:
    """Create the service with mocked dependencies."""

    storage_service = Mock(
        spec=S3NewsStorageService
    )

    storage_service.save_raw_payload = AsyncMock()
    storage_service.save_article = AsyncMock()
    storage_service.save_rejected_payload = AsyncMock()

    source_repository = Mock(
        spec=NewsSourceRepository
    )

    source_repository.get_or_create = AsyncMock()

    article_repository = Mock(
        spec=ArticleRepository
    )

    article_repository.get_by_url = AsyncMock()
    article_repository.get_by_content_hash = AsyncMock()
    article_repository.add = AsyncMock()
    article_repository.upsert_country_link = AsyncMock()
    article_repository.upsert_state_link = AsyncMock()

    service = IngestionPersistenceService(
        storage_service=storage_service,
        source_repository=source_repository,
        article_repository=article_repository,
    )

    return (
        service,
        storage_service,
        source_repository,
        article_repository,
    )


@pytest.mark.asyncio
async def test_store_raw_payload_delegates_to_s3(
) -> None:
    """Confirm raw provider payloads are stored."""

    (
        service,
        storage_service,
        _,
        _,
    ) = create_service()

    expected_location = S3ObjectLocation(
        bucket="world-news-test-bucket",
        key="raw/news/test.json",
        uri=(
            "s3://world-news-test-bucket/"
            "raw/news/test.json"
        ),
    )

    storage_service.save_raw_payload.return_value = (
        expected_location
    )

    result = await service.store_raw_payload(
        provider="GDELT",
        payload={
            "articles": [],
        },
        query="world news",
    )

    assert result == expected_location

    storage_service.save_raw_payload.assert_awaited_once_with(
        provider="GDELT",
        payload={
            "articles": [],
        },
        source_id=None,
        query="world news",
        extra_partitions=None,
    )


@pytest.mark.asyncio
async def test_article_is_persisted_successfully(
) -> None:
    """Confirm S3, source, article, and mappings are used."""

    (
        service,
        storage_service,
        source_repository,
        article_repository,
    ) = create_service()

    article = create_article()
    source_id = uuid4()

    article_repository.get_by_url.return_value = None
    article_repository.get_by_content_hash.return_value = (
        None
    )

    source_repository.get_or_create.return_value = (
        NewsSourceRecord(
            id=source_id,
            name="Example News",
            source_type="RSS",
            country_code="IN",
        ),
        True,
    )

    storage_service.save_article.return_value = (
        S3ObjectLocation(
            bucket="world-news-test-bucket",
            key="processed/news/article.json",
            uri=(
                "s3://world-news-test-bucket/"
                "processed/news/article.json"
            ),
        )
    )

    result = await service.persist_article(
        article=article,
        raw_s3_uri=(
            "s3://world-news-test-bucket/"
            "raw/news/provider-response.json"
        ),
        country_scores={
            "IN": Decimal("1.0000"),
            "US": Decimal("0.9000"),
        },
        state_scores={
            "IN-TG": Decimal("0.9500"),
        },
        primary_state_code="IN-TG",
        state_detection_method="keyword",
    )

    assert result.status == PersistenceStatus.STORED
    assert result.article_id == article.article_id
    assert result.source_created is True
    assert result.raw_s3_uri == (
        "s3://world-news-test-bucket/"
        "raw/news/provider-response.json"
    )
    assert result.processed_s3_uri == (
        "s3://world-news-test-bucket/"
        "processed/news/article.json"
    )

    storage_service.save_article.assert_awaited_once()

    source_repository.get_or_create.assert_awaited_once_with(
        name="Example News",
        source_type="RSS",
        homepage_url="https://example.com/",
        country_code="IN",
        credibility_score=None,
    )

    article_repository.add.assert_awaited_once()

    saved_record = (
        article_repository.add.await_args.args[0]
    )

    assert isinstance(saved_record, ArticleRecord)
    assert saved_record.id == article.article_id
    assert saved_record.source_id == source_id
    assert saved_record.title == article.title
    assert saved_record.url == str(article.url)
    assert saved_record.raw_s3_uri == (
        "s3://world-news-test-bucket/"
        "raw/news/provider-response.json"
    )
    assert saved_record.processed_s3_uri == (
        "s3://world-news-test-bucket/"
        "processed/news/article.json"
    )

    assert (
        article_repository
        .upsert_country_link
        .await_count
        == 2
    )

    country_calls = (
        article_repository
        .upsert_country_link
        .await_args_list
    )

    assert country_calls[0].kwargs == {
        "article_id": article.article_id,
        "country_code": "IN",
        "relevance_score": Decimal("1.0000"),
    }

    assert country_calls[1].kwargs == {
        "article_id": article.article_id,
        "country_code": "US",
        "relevance_score": Decimal("0.9000"),
    }

    article_repository.upsert_state_link.assert_awaited_once_with(
        article_id=article.article_id,
        state_code="IN-TG",
        relevance_score=Decimal("0.9500"),
        is_primary=True,
        detection_method="keyword",
    )


@pytest.mark.asyncio
async def test_duplicate_url_skips_article_storage(
) -> None:
    """Confirm duplicate URLs are not saved again."""

    (
        service,
        storage_service,
        source_repository,
        article_repository,
    ) = create_service()

    article = create_article()
    existing_article_id = uuid4()

    article_repository.get_by_url.return_value = (
        ArticleRecord(
            id=existing_article_id,
            source_id=uuid4(),
            title="Existing article",
            url=str(article.url),
            published_at=article.published_at,
            primary_category="General",
            language_code="en",
            processed_s3_uri=(
                "s3://bucket/processed/existing.json"
            ),
        )
    )

    result = await service.persist_article(
        article=article,
        raw_s3_uri="s3://bucket/raw/test.json",
    )

    assert result.status == (
        PersistenceStatus.DUPLICATE
    )
    assert result.article_id == existing_article_id
    assert result.duplicate_reason == "url"
    assert result.raw_s3_uri == (
        "s3://bucket/raw/test.json"
    )
    assert result.processed_s3_uri == (
        "s3://bucket/processed/existing.json"
    )

    storage_service.save_article.assert_not_awaited()
    source_repository.get_or_create.assert_not_awaited()
    article_repository.add.assert_not_awaited()
    article_repository.get_by_content_hash.assert_not_awaited()
    article_repository.upsert_country_link.assert_not_awaited()
    article_repository.upsert_state_link.assert_not_awaited()


@pytest.mark.asyncio
async def test_duplicate_hash_is_detected(
) -> None:
    """Confirm content hashes detect duplicates."""

    (
        service,
        storage_service,
        source_repository,
        article_repository,
    ) = create_service()

    article = create_article()
    existing_article_id = uuid4()

    article_repository.get_by_url.return_value = None

    article_repository.get_by_content_hash.return_value = (
        ArticleRecord(
            id=existing_article_id,
            source_id=uuid4(),
            title="Existing hashed article",
            url="https://example.com/existing",
            published_at=article.published_at,
            primary_category="General",
            language_code="en",
        )
    )

    result = await service.persist_article(
        article=article
    )

    assert result.status == (
        PersistenceStatus.DUPLICATE
    )
    assert result.article_id == existing_article_id
    assert result.duplicate_reason == (
        "content_hash"
    )

    article_repository.get_by_url.assert_awaited_once_with(
        str(article.url)
    )

    article_repository.get_by_content_hash.assert_awaited_once_with(
        "a" * 64
    )

    storage_service.save_article.assert_not_awaited()
    source_repository.get_or_create.assert_not_awaited()
    article_repository.add.assert_not_awaited()
    article_repository.upsert_country_link.assert_not_awaited()
    article_repository.upsert_state_link.assert_not_awaited()


@pytest.mark.asyncio
async def test_raw_storage_error_is_converted(
) -> None:
    """Confirm S3 raw failures use a service error."""

    (
        service,
        storage_service,
        _,
        _,
    ) = create_service()

    storage_service.save_raw_payload.side_effect = (
        RuntimeError("S3 unavailable")
    )

    with pytest.raises(
        RawPayloadPersistenceError,
        match="S3 unavailable",
    ):
        await service.store_raw_payload(
            provider="GDELT",
            payload={},
        )


@pytest.mark.asyncio
async def test_article_failure_is_converted(
) -> None:
    """Confirm article failures use a service error."""

    (
        service,
        storage_service,
        source_repository,
        article_repository,
    ) = create_service()

    article_repository.get_by_url.side_effect = (
        RuntimeError("Database unavailable")
    )

    with pytest.raises(
        ArticlePersistenceError,
        match="Database unavailable",
    ):
        await service.persist_article(
            article=create_article()
        )

    storage_service.save_article.assert_not_awaited()
    source_repository.get_or_create.assert_not_awaited()
    article_repository.add.assert_not_awaited()


def test_relevance_scores_are_validated() -> None:
    """Confirm location scores remain between zero and one."""

    result = normalize_relevance_scores(
        {
            " in-tg ": Decimal("0.95"),
            " us ": 1,
        }
    )

    assert result == {
        "IN-TG": Decimal("0.95"),
        "US": Decimal("1"),
    }

    with pytest.raises(
        ValueError,
        match="between 0 and 1",
    ):
        normalize_relevance_scores(
            {
                "IN-TG": Decimal("1.50"),
            }
        )

    with pytest.raises(
        ValueError,
        match="cannot be empty",
    ):
        normalize_relevance_scores(
            {
                "   ": Decimal("0.50"),
            }
        )
