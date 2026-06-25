"""Base interface for all news ingestion providers."""

from abc import ABC, abstractmethod
from typing import Any

from src.models import Article


class NewsProvider(ABC):
    """Abstract base class implemented by every news provider."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the human-readable name of the news provider."""

    @abstractmethod
    def fetch_articles(self, **kwargs: Any) -> list[Article]:
        """Fetch and return normalized news articles."""