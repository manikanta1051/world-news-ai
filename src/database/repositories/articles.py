from collections.abc import Sequence
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    ArticleCountryRecord,
    ArticleRecord,
    ArticleStateRecord,
)
from src.database.repositories.validators import (
    validate_result_limit,
)


class ArticleRepository:
    """Database operations for articles."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def add(
        self,
        article: ArticleRecord,
    ) -> ArticleRecord:
        """Add an article to the transaction."""

        self.session.add(article)
        await self.session.flush()

        return article

    async def get_by_id(
        self,
        article_id: UUID,
    ) -> ArticleRecord | None:
        """Return an article by ID."""

        return await self.session.get(
            ArticleRecord,
            article_id,
        )

    async def get_by_url(
        self,
        url: str,
    ) -> ArticleRecord | None:
        """Find an article by URL."""

        statement = select(
            ArticleRecord
        ).where(
            or_(
                ArticleRecord.url == url,
                ArticleRecord.canonical_url == url,
            )
        )

        result = await self.session.scalars(
            statement
        )

        return result.first()

    async def get_by_content_hash(
        self,
        content_hash: str,
    ) -> ArticleRecord | None:
        """Find an article by content hash."""

        statement = select(
            ArticleRecord
        ).where(
            ArticleRecord.content_hash
            == content_hash
        )

        result = await self.session.scalars(
            statement
        )

        return result.first()

    async def list_recent(
        self,
        *,
        limit: int = 50,
        category: str | None = None,
        language_code: str | None = None,
    ) -> Sequence[ArticleRecord]:
        """Return recent articles."""

        validate_result_limit(limit)

        statement = select(ArticleRecord)

        if category is not None:
            statement = statement.where(
                ArticleRecord.primary_category
                == category
            )

        if language_code is not None:
            statement = statement.where(
                ArticleRecord.language_code
                == language_code
            )

        statement = (
            statement
            .order_by(
                ArticleRecord.published_at.desc()
            )
            .limit(limit)
        )

        result = await self.session.scalars(
            statement
        )

        return result.all()

    async def list_for_state(
        self,
        state_code: str,
        *,
        limit: int = 50,
    ) -> Sequence[ArticleRecord]:
        """Return articles for an Indian state."""

        validate_result_limit(limit)

        statement = (
            select(ArticleRecord)
            .join(
                ArticleStateRecord,
                ArticleStateRecord.article_id
                == ArticleRecord.id,
            )
            .where(
                ArticleStateRecord.state_code
                == state_code
            )
            .order_by(
                ArticleStateRecord
                .relevance_score
                .desc(),
                ArticleRecord.published_at.desc(),
            )
            .limit(limit)
        )

        result = await self.session.scalars(
            statement
        )

        return result.all()

    async def update_ai_results(
        self,
        article_id: UUID,
        *,
        summary: str | None,
        sentiment: str,
        keywords: list[str],
        share_caption: str | None = None,
        social_card_data: (
            dict[str, object] | None
        ) = None,
    ) -> bool:
        """Store article AI results."""

        statement = (
            update(ArticleRecord)
            .where(
                ArticleRecord.id == article_id
            )
            .values(
                summary=summary,
                sentiment=sentiment,
                keywords=keywords,
                share_caption=share_caption,
                social_card_data=(
                    social_card_data or {}
                ),
                ai_processed=True,
            )
        )

        result = await self.session.execute(
            statement
        )

        return bool(result.rowcount)

    async def upsert_country_link(
        self,
        *,
        article_id: UUID,
        country_code: str,
        relevance_score: Decimal,
    ) -> None:
        """Create or update an article-country link."""

        statement = insert(
            ArticleCountryRecord
        ).values(
            article_id=article_id,
            country_code=country_code,
            relevance_score=relevance_score,
        )

        statement = statement.on_conflict_do_update(
            index_elements=[
                ArticleCountryRecord.article_id,
                ArticleCountryRecord.country_code,
            ],
            set_={
                "relevance_score": relevance_score,
            },
        )

        await self.session.execute(statement)

    async def upsert_state_link(
        self,
        *,
        article_id: UUID,
        state_code: str,
        relevance_score: Decimal,
        is_primary: bool = False,
        detection_method: str | None = None,
    ) -> None:
        """Create or update an article-state link."""

        statement = insert(
            ArticleStateRecord
        ).values(
            article_id=article_id,
            state_code=state_code,
            relevance_score=relevance_score,
            is_primary=is_primary,
            detection_method=detection_method,
        )

        statement = statement.on_conflict_do_update(
            index_elements=[
                ArticleStateRecord.article_id,
                ArticleStateRecord.state_code,
            ],
            set_={
                "relevance_score": relevance_score,
                "is_primary": is_primary,
                "detection_method": detection_method,
            },
        )

        await self.session.execute(statement)