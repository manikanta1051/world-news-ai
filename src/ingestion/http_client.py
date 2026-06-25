import logging
from collections.abc import Mapping
from typing import Any

import httpx
from tenacity import (
    AsyncRetrying,
    before_sleep_log,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.common.config import settings
from src.common.logging_config import logger
from src.ingestion.exceptions import (
    HttpRequestFailedError,
    HttpResponseDecodeError,
    HttpResponseStatusError,
)


RequestParams = Mapping[
    str,
    str | int | float | bool,
]

JsonResponse = dict[str, Any] | list[Any]


class AsyncNewsHttpClient:
    """Reusable asynchronous HTTP client for news providers."""

    def __init__(
        self,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._owns_client = client is None
        self._client = client or self._create_client()

    @staticmethod
    def _create_client() -> httpx.AsyncClient:
        """Create the configured HTTPX client."""

        timeout = httpx.Timeout(
            settings.http_timeout_seconds
        )

        limits = httpx.Limits(
            max_connections=settings.http_max_connections,
            max_keepalive_connections=(
                settings.http_max_keepalive_connections
            ),
        )

        headers = {
            "User-Agent": settings.http_user_agent,
            "Accept": (
                "application/json, "
                "text/plain;q=0.9, "
                "*/*;q=0.8"
            ),
        }

        return httpx.AsyncClient(
            timeout=timeout,
            limits=limits,
            headers=headers,
            follow_redirects=True,
        )

    async def __aenter__(self) -> "AsyncNewsHttpClient":
        """Enter the asynchronous context manager."""

        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Close owned HTTP resources."""

        await self.close()

    async def close(self) -> None:
        """Close the internally created HTTP client."""

        if self._owns_client:
            await self._client.aclose()

    async def get_response(
        self,
        url: str,
        params: RequestParams | None = None,
    ) -> httpx.Response:
        """Send a GET request with retry handling."""

        retryable_errors = (
            httpx.TimeoutException,
            httpx.NetworkError,
        )

        try:
            async for attempt in AsyncRetrying(
                stop=stop_after_attempt(
                    settings.http_retry_attempts
                ),
                wait=wait_exponential(
                    multiplier=1,
                    min=settings.http_retry_min_wait_seconds,
                    max=settings.http_retry_max_wait_seconds,
                ),
                retry=retry_if_exception_type(
                    retryable_errors
                ),
                before_sleep=before_sleep_log(
                    logger,
                    logging.WARNING,
                ),
                reraise=True,
            ):
                with attempt:
                    attempt_number = (
                        attempt.retry_state.attempt_number
                    )

                    logger.info(
                        "Sending GET request url=%s attempt=%s",
                        url,
                        attempt_number,
                    )

                    response = await self._client.get(
                        url,
                        params=params,
                    )

                    response.raise_for_status()

                    logger.info(
                        "GET request succeeded url=%s status=%s",
                        response.url,
                        response.status_code,
                    )

                    return response

        except httpx.HTTPStatusError as exc:
            logger.error(
                "HTTP status error url=%s status=%s",
                exc.request.url,
                exc.response.status_code,
            )

            raise HttpResponseStatusError(
                (
                    "HTTP request returned an unexpected status code: "
                    f"{response.status_code} for {response.url}"
                ),
                status_code=response.status_code,
                url=str(response.url),
            ) from exc

        except retryable_errors as exc:
            logger.error(
                "HTTP request failed after retries "
                "url=%s error=%s",
                url,
                exc,
            )

            raise HttpRequestFailedError(
                url=url,
                detail=str(exc),
            ) from exc

        raise RuntimeError(
            "HTTP retry loop ended without a response."
        )

    async def get_json(
        self,
        url: str,
        params: RequestParams | None = None,
    ) -> JsonResponse:
        """Send a GET request and decode its JSON body."""

        response = await self.get_response(
            url=url,
            params=params,
        )

        try:
            data = response.json()
        except ValueError as exc:
            logger.error(
                "Failed to decode JSON response url=%s",
                response.url,
            )

            raise HttpResponseDecodeError(
                url=str(response.url)
            ) from exc

        if not isinstance(data, dict | list):
            raise HttpResponseDecodeError(
                url=str(response.url)
            )

        return data

    async def get_text(
        self,
        url: str,
        params: RequestParams | None = None,
    ) -> str:
        """Send a GET request and return its text body."""

        response = await self.get_response(
            url=url,
            params=params,
        )

        return response.text