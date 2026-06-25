import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.models import (
    Article,
    ArticleLabel,
    NewsCategory,
    NewsSource,
    SocialCardData,
    SourceType,
    get_country_name,
    normalize_country_code,
)


FIXTURE_FILE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "sample_article.json"
)


def test_news_category_and_label_values() -> None:
    """Confirm that important category and label values are available."""

    assert NewsCategory.DEFENCE_SECURITY == "Defence & Security"
    assert NewsCategory.ENERGY == "Energy"
    assert ArticleLabel.BREAKING == "Breaking"
    assert ArticleLabel.TRENDING == "Trending"


def test_country_code_is_normalized() -> None:
    """Confirm that lowercase country codes are converted to uppercase."""

    assert normalize_country_code("in") == "IN"
    assert normalize_country_code(" us ") == "US"
    assert get_country_name("GB") == "United Kingdom"


def test_invalid_country_code_is_rejected() -> None:
    """Confirm that unknown or incorrectly sized country codes fail."""

    with pytest.raises(ValueError):
        normalize_country_code("IND")

    with pytest.raises(ValueError):
        normalize_country_code("XX")


def test_news_source_is_validated() -> None:
    """Confirm that source information is normalized correctly."""

    source = NewsSource(
        name="Reuters",
        source_type=SourceType.RSS,
        homepage_url="https://www.reuters.com",
        country_code="gb",
        credibility_score=95,
    )

    assert source.name == "Reuters"
    assert source.country_code == "GB"
    assert source.credibility_score == 95


def test_invalid_source_credibility_score_is_rejected() -> None:
    """Confirm that credibility scores cannot exceed 100."""

    with pytest.raises(ValidationError):
        NewsSource(
            name="Invalid Source",
            source_type=SourceType.MANUAL,
            credibility_score=101,
        )


def test_article_normalizes_countries_keywords_and_time() -> None:
    """Confirm article fields are normalized during validation."""

    source = NewsSource(
        name="Example News",
        source_type=SourceType.RSS,
    )

    article = Article(
        title="India announces a new energy agreement",
        url="https://example.com/energy-agreement",
        source=source,
        published_at=datetime(
            2026,
            6,
            25,
            10,
            30,
        ),
        primary_category=NewsCategory.ENERGY,
        country_codes=["in", "US", "in"],
        keywords=[
            "Energy",
            " energy ",
            "India",
            "",
        ],
    )

    assert article.country_codes == ["IN", "US"]
    assert article.keywords == ["Energy", "India"]
    assert article.published_at.tzinfo == timezone.utc
    assert article.primary_category == NewsCategory.ENERGY


def test_invalid_article_url_and_hash_are_rejected() -> None:
    """Confirm that malformed URLs and content hashes fail validation."""

    source = NewsSource(
        name="Example News",
        source_type=SourceType.RSS,
    )

    with pytest.raises(ValidationError):
        Article(
            title="Example valid article title",
            url="not-a-valid-url",
            source=source,
            published_at=datetime.now(timezone.utc),
        )

    with pytest.raises(ValidationError):
        Article(
            title="Example valid article title",
            url="https://example.com/article",
            source=source,
            published_at=datetime.now(timezone.utc),
            content_hash="invalid-hash",
        )


def test_sample_article_json_loads_successfully() -> None:
    """Confirm that the complete sample article can be validated."""

    article_json = FIXTURE_FILE.read_text(encoding="utf-8")
    article = Article.model_validate_json(article_json)

    assert article.title == (
        "India announces a new renewable energy project"
    )
    assert article.source.country_code == "IN"
    assert article.primary_category == NewsCategory.ENERGY
    assert article.country_codes == ["IN", "US"]
    assert article.keywords == [
        "Renewable Energy",
        "India",
    ]
    assert article.ai_processed is True
    assert article.published_at.tzinfo == timezone.utc
    assert article.social_card.is_generated is False


def test_social_card_defaults_are_available() -> None:
    """Confirm that a social card has safe default values."""

    social_card = SocialCardData()

    assert social_card.template_name == "standard"
    assert social_card.is_generated is False
    assert social_card.generated_image_path is None


def test_article_can_be_serialized_to_json() -> None:
    """Confirm that validated article data can be exported as JSON."""

    article_data = json.loads(
        FIXTURE_FILE.read_text(encoding="utf-8")
    )

    article = Article.model_validate(article_data)
    exported_json = article.model_dump_json()
    exported_data = json.loads(exported_json)

    assert exported_data["primary_category"] == "Energy"
    assert exported_data["source"]["source_type"] == "RSS"
    assert exported_data["country_codes"] == ["IN", "US"]