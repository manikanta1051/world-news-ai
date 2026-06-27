from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import NewsSourceRecord
from src.database.repositories.validators import (
    validate_result_limit,
)


class NewsSourceRepository:
    """Database operations for news sources."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def add(
        self,
        source: NewsSourceRecord,
    ) -> NewsSourceRecord:
        """Add a news source to the transaction."""

        self.session.add(source)
        await self.session.flush()

        return source

    async def get_by_id(
        self,
        source_id: UUID,
    ) -> NewsSourceRecord | None:
        """Return a news source by ID."""

        return await self.session.get(
            NewsSourceRecord,
            source_id,
        )

    async def get_by_name_and_type(
        self,
        name: str,
        source_type: str,
    ) -> NewsSourceRecord | None:
        """Find a source using its unique fields."""

        statement = select(
            NewsSourceRecord
        ).where(
            NewsSourceRecord.name == name,
            NewsSourceRecord.source_type
            == source_type,
        )

        result = await self.session.scalars(
            statement
        )

        return result.first()

    async def list_active(
        self,
        limit: int = 100,
    ) -> Sequence[NewsSourceRecord]:
        """Return active news sources."""

        validate_result_limit(limit)

        statement = (
            select(NewsSourceRecord)
            .where(
                NewsSourceRecord.is_active.is_(True)
            )
            .order_by(
                NewsSourceRecord.name.asc()
            )
            .limit(limit)
        )

        result = await self.session.scalars(
            statement
        )

        return result.all()

    async def get_or_create(
        self,
        *,
        name: str,
        source_type: str,
        homepage_url: str | None = None,
        country_code: str | None = None,
        credibility_score: Decimal | None = None,
        extra_metadata: dict[str, object] | None = None,
    ) -> tuple[NewsSourceRecord, bool]:
        """Return an existing source or create one."""

        existing_source = (
            await self.get_by_name_and_type(
                name=name,
                source_type=source_type,
            )
        )

        if existing_source is not None:
            return existing_source, False

        new_source = NewsSourceRecord(
            name=name,
            source_type=source_type,
            homepage_url=homepage_url,
            country_code=country_code,
            credibility_score=credibility_score,
            extra_metadata=extra_metadata or {},
        )

        await self.add(new_source)

        return new_source, True