import asyncio
from typing import Any

import pytest
from pydantic import ValidationError

from src.ingestion.exceptions import (
    NewsProviderResponseError,
)
from src.ingestion.providers.gdelt import (
    GdeltNewsProvider,
    GdeltSearchRequest,
)


class FakeHttpClient:
    """Return a fixed JSON-compatible response."""

    def __init__(
        self,
        response_data: object,
    ) -> None:
        self.response_data = response_data
        self.last_url: str | None = None
        self.last_params: dict[
            str,
            str | int,
        ] | None = None
        self.closed = False

    async def get_json(
        self,
        *,
        url: str,
        params: dict[str, str | int],
    ) -> Any:
        """Return the configured response."""

        self.last_url = url
        self.last_params = params

        return self.response_data

    async def close(self) -> None:
        """Record that the client was closed."""

        self.closed = True


def valid_raw_article(
    *,
    title: str = "India technology update",
    url: str = "https://example.com/news/one",
) -> dict[str, object]:
    """Create one valid GDELT article payload."""

    return {
        "title": title,
        "url": url,
        "seendate": "20260628T120000Z",
        "domain": "example.com",
        "sourcecountry": "India",
        "language": "English",
        "socialimage": (
            "https://example.com/image.jpg"
        ),
    }


def test_gdelt_search_request_accepts_valid_values(
) -> None:
    """Confirm valid search options are normalized."""

    request = GdeltSearchRequest(
        query="  India technology  ",
        max_records=50,
        timespan="24H",
    )

    assert request.query == "India technology"
    assert request.max_records == 50
    assert request.timespan == "24h"


def test_gdelt_search_request_rejects_invalid_values(
) -> None:
    """Confirm invalid search options are rejected."""

    with pytest.raises(ValidationError):
        GdeltSearchRequest(
            query="AI",
        )

    with pytest.raises(ValidationError):
        GdeltSearchRequest(
            query="world news",
            max_records=251,
        )

    with pytest.raises(ValidationError):
        GdeltSearchRequest(
            query="world news",
            timespan="10min",
        )


def test_fetch_batch_preserves_raw_response_and_rejections(
) -> None:
    """Confirm raw data and rejected records are retained."""

    raw_payload = {
        "articles": [
            valid_raw_article(),
            {
                "title": "",
                "url": (
                    "https://example.com/news/two"
                ),
                "seendate": "20260628T130000Z",
            },
            "invalid-non-object",
        ],
    }

    fake_client = FakeHttpClient(raw_payload)

    provider = GdeltNewsProvider(
        http_client=fake_client,
    )

    result = asyncio.run(
        provider.fetch_batch(
            query="India technology",
            max_records=20,
            timespan="24h",
        )
    )

    assert result.provider_name == "GDELT"
    assert result.raw_payload is raw_payload
    assert result.received_count == 3
    assert len(result.articles) == 1
    assert len(result.rejected_items) == 2

    article = result.articles[0]

    assert article.title == (
        "India technology update"
    )
    assert str(article.url) == (
        "https://example.com/news/one"
    )
    assert article.source.country_code == "IN"
    assert article.language_code == "en"

    assert (
        "title cannot be empty"
        in result.rejected_items[0].reason
    )
    assert result.rejected_items[
        0
    ].source_id == (
        "https://example.com/news/two"
    )

    assert result.rejected_items[
        1
    ].payload == "invalid-non-object"
    assert result.rejected_items[
        1
    ].source_id is None

    assert fake_client.last_params == {
        "query": "India technology",
        "mode": "artlist",
        "maxrecords": 20,
        "timespan": "24h",
        "sort": "datedesc",
        "format": "json",
    }


def test_fetch_articles_returns_only_validated_articles(
) -> None:
    """Confirm the legacy method remains supported."""

    fake_client = FakeHttpClient(
        {
            "articles": [
                valid_raw_article(),
                {
                    "title": "",
                    "url": (
                        "https://example.com/invalid"
                    ),
                    "seendate": (
                        "20260628T130000Z"
                    ),
                },
            ],
        }
    )

    provider = GdeltNewsProvider(
        http_client=fake_client,
    )

    articles = asyncio.run(
        provider.fetch_articles(
            query="world news",
        )
    )

    assert len(articles) == 1
    assert articles[0].title == (
        "India technology update"
    )


def test_gdelt_provider_rejects_non_object_response(
) -> None:
    """Confirm the top-level response must be an object."""

    provider = GdeltNewsProvider(
        http_client=FakeHttpClient(
            ["invalid"]
        ),
    )

    with pytest.raises(
        NewsProviderResponseError
    ):
        asyncio.run(
            provider.fetch_batch(
                query="world news",
            )
        )


def test_gdelt_provider_rejects_missing_articles_field(
) -> None:
    """Confirm a response without articles is rejected."""

    provider = GdeltNewsProvider(
        http_client=FakeHttpClient(
            {
                "status": "success",
            }
        ),
    )

    with pytest.raises(
        NewsProviderResponseError
    ):
        asyncio.run(
            provider.fetch_batch(
                query="world news",
            )
        )


def test_gdelt_provider_rejects_non_list_articles_field(
) -> None:
    """Confirm the articles field must be a list."""

    provider = GdeltNewsProvider(
        http_client=FakeHttpClient(
            {
                "articles": {
                    "title": "Not a list",
                },
            }
        ),
    )

    with pytest.raises(
        NewsProviderResponseError
    ):
        asyncio.run(
            provider.fetch_batch(
                query="world news",
            )
        )
