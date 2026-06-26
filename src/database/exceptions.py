class DatabaseError(RuntimeError):
    """Base exception for database-related failures."""


class DatabaseConfigurationError(DatabaseError):
    """Raised when database configuration is incomplete."""

    def __init__(self, detail: str) -> None:
        self.detail = detail

        super().__init__(
            f"Database configuration is invalid: {detail}"
        )


class DatabaseSecretError(DatabaseError):
    """Raised when database credentials cannot be retrieved."""

    def __init__(
        self,
        secret_id: str,
        detail: str,
    ) -> None:
        self.secret_id = secret_id
        self.detail = detail

        super().__init__(
            "Unable to retrieve database credentials "
            f"from AWS Secrets Manager: {detail}"
        )


class DatabaseConnectionError(DatabaseError):
    """Raised when PostgreSQL cannot be reached."""

    def __init__(self, detail: str) -> None:
        self.detail = detail

        super().__init__(
            f"PostgreSQL connection failed: {detail}"
        )