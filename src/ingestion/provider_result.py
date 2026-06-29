from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.models import Article


@dataclass(frozen=True, slots=True)
class ProviderRejectedItem:
    """One provider record rejected during mapping or validation."""

    payload: object
    reason: str
    source_id: str | None = None
    extra_partitions: Mapping[str, object] | None = None


@dataclass(frozen=True, slots=True)
class ProviderFetchResult:
    """Complete result returned by a raw-capable news provider."""

    provider_name: str
    raw_payload: object
    articles: tuple[Article, ...]
    received_count: int
    rejected_items: tuple[ProviderRejectedItem, ...] = ()

    def __post_init__(self) -> None:
        normalized_provider = self.provider_name.strip()

        if not normalized_provider:
            raise ValueError(
                "Provider name cannot be empty."
            )

        if self.received_count < 0:
            raise ValueError(
                "received_count cannot be negative."
            )

        processed_count = (
            len(self.articles)
            + len(self.rejected_items)
        )

        if self.received_count < processed_count:
            raise ValueError(
                "received_count cannot be smaller than "
                "the validated and rejected record count."
            )

        object.__setattr__(
            self,
            "provider_name",
            normalized_provider,
        )
