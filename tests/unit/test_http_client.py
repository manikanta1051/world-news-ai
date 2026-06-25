import asyncio

import httpx
import pytest

from src.common.config import settings
from src.ingestion import (
    AsyncNewsHttpClient,
    HttpRequestFailedError,
    HttpResponseDecodeError,
    HttpResponseStatusError,
)


def test_get_json_returns_decoded_response() -> None:
    """Confirm that a successful JSON response is decoded."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "articles": [
                    {
                        "title": "Example article",
                    }
                ]
            },
            request=request,
        )

    async def scenario() -> dict[str, object] | list[object]:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
        ) as raw_client:
            client = AsyncNewsHttpClient(
                client=raw_client,
            )

            return await client.get_json(
                "https://example.com/news"
            )

    result = asyncio.run(scenario())

    assert isinstance(result, dict)
    assert "articles" in result
    assert len(result["articles"]) == 1


def test_http_status_error_is_converted() -> None:
    """Confirm that unsuccessful HTTP statuses use project errors."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=404,
            json={
                "message": "Not found",
            },
            request=request,
        )

    async def scenario() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
        ) as raw_client:
            client = AsyncNewsHttpClient(
                client=raw_client,
            )

            await client.get_response(
                "https://example.com/missing"
            )

    with pytest.raises(
        HttpResponseStatusError
    ) as error:
        asyncio.run(scenario())

    assert error.value.status_code == 404
    assert "example.com/missing" in error.value.url


def test_invalid_json_response_is_rejected() -> None:
    """Confirm that invalid JSON raises a clear project error."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            content=b"This is not JSON",
            headers={
                "Content-Type": "text/plain",
            },
            request=request,
        )

    async def scenario() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
        ) as raw_client:
            client = AsyncNewsHttpClient(
                client=raw_client,
            )

            await client.get_json(
                "https://example.com/invalid-json"
            )

    with pytest.raises(HttpResponseDecodeError):
        asyncio.run(scenario())


def test_temporary_timeout_is_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirm that temporary timeouts are retried."""

    request_count = 0

    monkeypatch.setattr(
        settings,
        "http_retry_attempts",
        3,
    )
    monkeypatch.setattr(
        settings,
        "http_retry_min_wait_seconds",
        0.0,
    )
    monkeypatch.setattr(
        settings,
        "http_retry_max_wait_seconds",
        0.0,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count

        request_count += 1

        if request_count < 3:
            raise httpx.ReadTimeout(
                "Temporary timeout",
                request=request,
            )

        return httpx.Response(
            status_code=200,
            json={
                "status": "success",
            },
            request=request,
        )

    async def scenario() -> dict[str, object] | list[object]:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
        ) as raw_client:
            client = AsyncNewsHttpClient(
                client=raw_client,
            )

            return await client.get_json(
                "https://example.com/retry"
            )

    result = asyncio.run(scenario())

    assert request_count == 3
    assert result == {
        "status": "success",
    }


def test_request_failure_after_all_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Confirm that repeated network failures use a project error."""

    request_count = 0

    monkeypatch.setattr(
        settings,
        "http_retry_attempts",
        2,
    )
    monkeypatch.setattr(
        settings,
        "http_retry_min_wait_seconds",
        0.0,
    )
    monkeypatch.setattr(
        settings,
        "http_retry_max_wait_seconds",
        0.0,
    )

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count

        request_count += 1

        raise httpx.ReadTimeout(
            "Service unavailable",
            request=request,
        )

    async def scenario() -> None:
        transport = httpx.MockTransport(handler)

        async with httpx.AsyncClient(
            transport=transport,
        ) as raw_client:
            client = AsyncNewsHttpClient(
                client=raw_client,
            )

            await client.get_response(
                "https://example.com/unavailable"
            )

    with pytest.raises(HttpRequestFailedError):
        asyncio.run(scenario())

    assert request_count == 2