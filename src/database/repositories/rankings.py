from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    ArticleRecord,
    StateNewsRankingRecord,
)


@dataclass(
    frozen=True,
    slots=True,
)
class StateRankingInput:
    """Input data for one ranked state article."""

    article_id: UUID
    rank_position: int
    ranking_score: Decimal
    score_components: dict[str, object] = field(
        default_factory=dict
    )


def validate_state_rankings(
    rankings: Sequence[StateRankingInput],
) -> None:
    """Validate a complete Top 10 ranking list."""

    if len(rankings) > 10:
        raise ValueError(
            "A state-news ranking cannot contain "
            "more than 10 articles."
        )

    rank_positions = [
        ranking.rank_position
        for ranking in rankings
    ]

    article_ids = [
        ranking.article_id
        for ranking in rankings
    ]

    if len(rank_positions) != len(
        set(rank_positions)
    ):
        raise ValueError(
            "Ranking positions must be unique."
        )

    if len(article_ids) != len(
        set(article_ids)
    ):
        raise ValueError(
            "An article cannot appear more than "
            "once in the same ranking."
        )

    for ranking in rankings:
        if not 1 <= ranking.rank_position <= 10:
            raise ValueError(
                "Ranking positions must be "
                "between 1 and 10."
            )

        if ranking.ranking_score < 0:
            raise ValueError(
                "Ranking scores cannot be negative."
            )

    expected_positions = list(
        range(1, len(rankings) + 1)
    )

    if sorted(rank_positions) != expected_positions:
        raise ValueError(
            "Ranking positions must be sequential "
            "and start at 1."
        )


class StateRankingRepository:
    """Database operations for state news rankings."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def replace_top_ten(
        self,
        *,
        state_code: str,
        ranking_date: date,
        rankings: Sequence[StateRankingInput],
        ranking_window: str = "24h",
        category_filter: str = "all",
    ) -> Sequence[StateNewsRankingRecord]:
        """Replace one state's ranking snapshot."""

        validate_state_rankings(rankings)

        if not ranking_window.strip():
            raise ValueError(
                "Ranking window cannot be empty."
            )

        if not category_filter.strip():
            raise ValueError(
                "Category filter cannot be empty."
            )

        delete_statement = delete(
            StateNewsRankingRecord
        ).where(
            StateNewsRankingRecord.state_code
            == state_code,
            StateNewsRankingRecord.ranking_date
            == ranking_date,
            StateNewsRankingRecord.ranking_window
            == ranking_window,
            StateNewsRankingRecord.category_filter
            == category_filter,
        )

        await self.session.execute(
            delete_statement
        )

        ranking_records = [
            StateNewsRankingRecord(
                state_code=state_code,
                article_id=ranking.article_id,
                ranking_date=ranking_date,
                ranking_window=ranking_window,
                category_filter=category_filter,
                rank_position=ranking.rank_position,
                ranking_score=ranking.ranking_score,
                score_components=(
                    ranking.score_components
                ),
            )
            for ranking in rankings
        ]

        if ranking_records:
            self.session.add_all(
                ranking_records
            )

        await self.session.flush()

        return ranking_records

    async def list_rankings(
        self,
        *,
        state_code: str,
        ranking_date: date,
        ranking_window: str = "24h",
        category_filter: str = "all",
    ) -> Sequence[StateNewsRankingRecord]:
        """Return one Top 10 ranking snapshot."""

        statement = (
            select(StateNewsRankingRecord)
            .where(
                StateNewsRankingRecord.state_code
                == state_code,
                StateNewsRankingRecord.ranking_date
                == ranking_date,
                StateNewsRankingRecord.ranking_window
                == ranking_window,
                StateNewsRankingRecord.category_filter
                == category_filter,
            )
            .order_by(
                StateNewsRankingRecord
                .rank_position
                .asc()
            )
            .limit(10)
        )

        result = await self.session.scalars(statement)

        return result.all()

    async def list_ranked_articles(
        self,
        *,
        state_code: str,
        ranking_date: date,
        ranking_window: str = "24h",
        category_filter: str = "all",
    ) -> list[
        tuple[
            StateNewsRankingRecord,
            ArticleRecord,
        ]
    ]:
        """Return ranking records with their articles."""

        statement = (
            select(
                StateNewsRankingRecord,
                ArticleRecord,
            )
            .join(
                ArticleRecord,
                ArticleRecord.id
                == StateNewsRankingRecord.article_id,
            )
            .where(
                StateNewsRankingRecord.state_code
                == state_code,
                StateNewsRankingRecord.ranking_date
                == ranking_date,
                StateNewsRankingRecord.ranking_window
                == ranking_window,
                StateNewsRankingRecord.category_filter
                == category_filter,
            )
            .order_by(
                StateNewsRankingRecord
                .rank_position
                .asc()
            )
            .limit(10)
        )

        result = await self.session.execute(
            statement
        )

        return [
            (row[0], row[1])
            for row in result.all()
        ]