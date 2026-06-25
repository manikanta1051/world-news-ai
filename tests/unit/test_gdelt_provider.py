import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from src.ingestion import (
    GdeltNewsProvider,
    GdeltSearchRequest,
    NewsProviderResponseError,
)
from src.ingestion.http_client import (
    JsonResponse,
    RequestParams,
)
from src.models import (
    NewsCategory,
    SourceType,
)


FIXTURE_FILE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "gdelt_response.json"
)


class FakeHttpClient:
    """Small fake client used for provider unit tests."""

    def __init__(
        self,
        response_data: JsonResponse,
    ) -> None:
        self.response_data = response_data
        self.last_url: str | None = None
        self.last_params: RequestParams | None = None

    async def get_json(
        self,
        url: str,
        params: RequestParams | None = None,
    ) -> JsonResponse:
        """Return the predefined fake response."""

        self.last_url = url
        self.last_params = params

        return self.response_data

    async def close(self) -> None:
        """Match the real HTTP client interface."""


def load_gdelt_fixture() -> dict[str, Any]:
    """Load the sample GDELT response."""

    return json.loads(
        FIXTURE_FILE.read_text(
            encoding="utf-8",
        )
    )


def test_gdelt_search_request_accepts_valid_values() -> None:
    """Confirm that valid GDELT search options are accepted."""

    request = GdeltSearchRequest(
        query="renewable energy",
        max_records=50,
        timespan="24h",
    )

    assert request.query == "renewable energy"
    assert request.max_records == 50
    assert request.timespan == "24h"


def test_gdelt_search_request_rejects_invalid_values() -> None:
    """Confirm that invalid search settings are rejected."""

    with pytest.raises(ValidationError):
        GdeltSearchRequest(
            query="AI",
            max_records=25,
            timespan="24h",
        )

    with pytest.raises(ValidationError):
        GdeltSearchRequest(
            query="renewable energy",
            max_records=251,
            timespan="24h",
        )

    with pytest.raises(ValidationError):
        GdeltSearchRequest(
            query="renewable energy",
            max_records=25,
            timespan="10min",
        )


def test_gdelt_provider_maps_and_skips_articles() -> None:
    """Confirm that valid articles are mapped and invalid ones skipped."""

    fake_client = FakeHttpClient(
        load_gdelt_fixture()
    )

    provider = GdeltNewsProvider(
        http_client=fake_client,
    )

    articles = asyncio.run(
        provider.fetch_articles(
            query="renewable energy",
            max_records=5,
            timespan="24h",
        )
    )

    assert provider.provider_name == "GDELT"
    assert len(articles) == 2

    first_article = articles[0]

    assert first_article.title == (
        "India expands its renewable energy partnership"
    )
    assert first_article.source.name == "example.com"
    assert first_article.source.source_type == SourceType.GDELT
    assert first_article.source.country_code == "IN"
    assert first_article.language_code == "en"
    assert first_article.primary_category == NewsCategory.GENERAL
    assert first_article.published_at == datetime(
        2026,
        6,
        25,
        14,
        30,
        tzinfo=timezone.utc,
    )

    second_article = articles[1]

    assert second_article.source.name == "news.example.org"
    assert second_article.source.country_code == "US"
    assert second_article.image_url is None

    assert fake_client.last_params is not None
    assert fake_client.last_params["mode"] == "artlist"
    assert fake_client.last_params["maxrecords"] == 5
    assert fake_client.last_params["timespan"] == "24h"
    assert fake_client.last_params["format"] == "json"


def test_gdelt_provider_rejects_non_object_response() -> None:
    """Confirm that a top-level JSON list is rejected."""

    fake_client = FakeHttpClient(
        [
            {
                "title": "Unexpected response",
            }
        ]
    )

    provider = GdeltNewsProvider(
        http_client=fake_client,
    )

    with pytest.raises(NewsProviderResponseError):
        asyncio.run(
            provider.fetch_articles(
                query="world news",
            )
        )


def test_gdelt_provider_rejects_missing_articles_field() -> None:
    """Confirm that a response without articles is rejected."""

    fake_client = FakeHttpClient(
        {
            "status": "success",
        }
    )

    provider = GdeltNewsProvider(
        http_client=fake_client,
    )

    with pytest.raises(
        NewsProviderResponseError
    ) as error:
        asyncio.run(
            provider.fetch_articles(
                query="world news",
            )
        )

    assert "articles field is missing" in str(
        error.value
    )