"""Custom exceptions used by the news ingestion layer."""

from typing import Any


class NewsIngestionError(Exception):
    """Base exception for all ingestion-related errors."""

    def __init__(
        self,
        message: str = "A news ingestion error occurred.",
        *args: Any,
        **context: Any,
    ) -> None:
        self.message = message
        self.context = context

        # Expose context values as exception attributes.
        # Example: error.status_code, error.url
        for key, value in context.items():
            setattr(self, key, value)

        detail = context.get("detail")
        display_message = message

        if detail:
            display_message = f"{message} {detail}"

        super().__init__(display_message, *args)


class HttpClientError(NewsIngestionError):
    """Base exception for reusable HTTP-client errors."""


class HttpRequestError(HttpClientError):
    """Raised when an HTTP request cannot be completed."""


class HttpRequestFailedError(HttpRequestError):
    """Raised when a request fails after all retry attempts."""


class HttpResponseError(HttpClientError):
    """Base exception for invalid HTTP responses."""


class HttpResponseStatusError(HttpResponseError):
    """Raised when a response has an unsuccessful HTTP status."""


class HttpResponseDecodeError(HttpResponseError):
    """Raised when an HTTP response body cannot be decoded."""


class NewsProviderError(NewsIngestionError):
    """Base exception for news-provider errors."""


class NewsProviderConfigurationError(NewsProviderError):
    """Raised when a news provider is incorrectly configured."""


class NewsProviderRequestError(NewsProviderError):
    """Raised when a provider request cannot be completed."""


class NewsProviderResponseError(NewsProviderError):
    """Raised when a provider returns invalid response data."""


class NewsProviderUnavailableError(NewsProviderError):
    """Raised when a provider is temporarily unavailable."""


class NewsProviderRateLimitError(NewsProviderError):
    """Raised when a provider rate limit is exceeded."""


__all__ = [
    "HttpClientError",
    "HttpRequestError",
    "HttpRequestFailedError",
    "HttpResponseDecodeError",
    "HttpResponseError",
    "HttpResponseStatusError",
    "NewsIngestionError",
    "NewsProviderConfigurationError",
    "NewsProviderError",
    "NewsProviderRateLimitError",
    "NewsProviderRequestError",
    "NewsProviderResponseError",
    "NewsProviderUnavailableError",
]
