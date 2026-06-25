"""Public exports for news ingestion providers."""

from src.ingestion.providers.base import NewsProvider
from src.ingestion.providers.gdelt import (
    GdeltNewsProvider,
    GdeltSearchRequest,
)

__all__ = [
    "GdeltNewsProvider",
    "GdeltSearchRequest",
    "NewsProvider",
]
