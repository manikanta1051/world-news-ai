class NewsIngestionError(RuntimeError):
    """Base exception for news-ingestion failures."""


class HttpRequestFailedError(NewsIngestionError):
    """Raised when an HTTP request fails after retries."""

    def __init__(self, url: str, detail: str) -> None:
        self.url = url
        self.detail = detail

        super().__init__(
            f"HTTP request failed for {url}: {detail}"
        )


class HttpResponseStatusError(NewsIngestionError):
    """Raised when a server returns an unsuccessful status."""

    def __init__(
        self,
        url: str,
        status_code: int,
    ) -> None:
        self.url = url
        self.status_code = status_code

        super().__init__(
            f"HTTP request to {url} returned "
            f"status code {status_code}."
        )


class HttpResponseDecodeError(NewsIngestionError):
    """Raised when a response cannot be decoded as JSON."""

    def __init__(self, url: str) -> None:
        self.url = url

        super().__init__(
            f"HTTP response from {url} did not contain valid JSON."
        )