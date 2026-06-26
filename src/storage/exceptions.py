class StorageError(RuntimeError):
    """Base exception for storage-related failures."""


class S3BucketNotConfiguredError(StorageError):
    """Raised when no S3 data bucket has been configured."""

    def __init__(self) -> None:
        super().__init__(
            "AWS_S3_DATA_BUCKET is not configured."
        )


class S3StorageError(StorageError):
    """Raised when an Amazon S3 operation fails."""

    def __init__(
        self,
        operation: str,
        bucket: str,
        key: str,
        detail: str,
    ) -> None:
        self.operation = operation
        self.bucket = bucket
        self.key = key
        self.detail = detail

        super().__init__(
            f"Amazon S3 {operation} failed for "
            f"s3://{bucket}/{key}: {detail}"
        )