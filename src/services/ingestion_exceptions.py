class IngestionPersistenceError(RuntimeError):
    """Base error for ingestion persistence failures."""

    def __init__(
        self,
        operation: str,
        detail: str,
    ) -> None:
        self.operation = operation
        self.detail = detail

        super().__init__(
            "Ingestion persistence failed during "
            f"{operation}: {detail}"
        )


class RawPayloadPersistenceError(
    IngestionPersistenceError
):
    """Raised when a raw provider payload cannot be saved."""

    def __init__(
        self,
        provider: str,
        detail: str,
    ) -> None:
        self.provider = provider

        super().__init__(
            operation="raw payload storage",
            detail=(
                f"provider={provider}; {detail}"
            ),
        )


class ArticlePersistenceError(
    IngestionPersistenceError
):
    """Raised when a validated article cannot be persisted."""

    def __init__(
        self,
        article_url: str,
        detail: str,
    ) -> None:
        self.article_url = article_url

        super().__init__(
            operation="article persistence",
            detail=(
                f"url={article_url}; {detail}"
            ),
        )


class RejectedPayloadPersistenceError(
    IngestionPersistenceError
):
    """Raised when a rejected payload cannot be saved."""

    def __init__(
        self,
        provider: str,
        detail: str,
    ) -> None:
        self.provider = provider

        super().__init__(
            operation="rejected payload storage",
            detail=(
                f"provider={provider}; {detail}"
            ),
        )