from datetime import date
from decimal import Decimal
from unittest.mock import (
    AsyncMock,
    Mock,
)
from uuid import uuid4

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.repositories import (
    IndiaLocationRepository,
    StateRankingInput,
    StateRankingRepository,
    UserPreferenceRepository,
    normalize_country_codes,
    validate_state_rankings,
)


def create_mock_session() -> Mock:
    """Create an AsyncSession-compatible mock."""

    session = Mock(spec=AsyncSession)

    session.add = Mock()
    session.add_all = Mock()
    session.flush = AsyncMock()
    session.get = AsyncMock()
    session.scalars = AsyncMock()
    session.execute = AsyncMock()

    return session


@pytest.mark.asyncio
async def test_location_repository_lists_active_states(
) -> None:
    """Confirm states are ordered for UI display."""

    session = create_mock_session()
    repository = IndiaLocationRepository(
        session
    )

    scalar_result = Mock()
    scalar_result.all.return_value = []

    session.scalars.return_value = scalar_result

    result = await repository.list_states(
        region_type="state"
    )

    assert result == []

    statement = session.scalars.await_args.args[0]

    compiled_sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={
                "literal_binds": True,
            },
        )
    )

    assert "indian_states.is_active IS true" in (
        compiled_sql
    )
    assert (
        "indian_states.region_type = 'state'"
        in compiled_sql
    )
    assert "ORDER BY" in compiled_sql


@pytest.mark.asyncio
async def test_invalid_region_type_is_rejected(
) -> None:
    """Confirm unsupported region types fail."""

    session = create_mock_session()
    repository = IndiaLocationRepository(
        session
    )

    with pytest.raises(
        ValueError,
        match="union_territory",
    ):
        await repository.list_states(
            region_type="province"
        )


@pytest.mark.asyncio
async def test_city_query_supports_district_filter(
) -> None:
    """Confirm cities can be filtered by district."""

    session = create_mock_session()
    repository = IndiaLocationRepository(
        session
    )

    scalar_result = Mock()
    scalar_result.all.return_value = []

    session.scalars.return_value = scalar_result

    district_id = uuid4()

    await repository.list_cities(
        "IN-TG",
        district_id=district_id,
        limit=20,
    )

    statement = session.scalars.await_args.args[0]

    compiled_sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
        )
    )

    assert "cities.state_code" in compiled_sql
    assert "cities.district_id" in compiled_sql
    assert "LIMIT" in compiled_sql


def test_country_codes_are_normalized() -> None:
    """Confirm favorite countries are normalized."""

    result = normalize_country_codes(
        [" us ", "in"]
    )

    assert result == ("US", "IN")


@pytest.mark.parametrize(
    ("country_codes", "message"),
    [
        (
            ["US", "IN", "GB"],
            "maximum of two",
        ),
        (
            ["US", "US"],
            "duplicate",
        ),
        (
            ["USA"],
            "exactly two",
        ),
    ],
)
def test_invalid_country_preferences_are_rejected(
    country_codes: list[str],
    message: str,
) -> None:
    """Confirm invalid favorite-country choices fail."""

    with pytest.raises(
        ValueError,
        match=message,
    ):
        normalize_country_codes(
            country_codes
        )


@pytest.mark.asyncio
async def test_replacing_favorite_countries_sets_priority(
) -> None:
    """Confirm priorities one and two are generated."""

    session = create_mock_session()
    repository = UserPreferenceRepository(
        session
    )

    user_id = uuid4()

    result = (
        await repository.replace_favorite_countries(
            user_id=user_id,
            country_codes=["US", "IN"],
        )
    )

    assert len(result) == 2
    assert result[0].country_code == "US"
    assert result[0].priority == 1
    assert result[1].country_code == "IN"
    assert result[1].priority == 2

    session.execute.assert_awaited_once()
    session.add_all.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_favorite_state_uses_on_conflict(
) -> None:
    """Confirm duplicate favorite states are ignored."""

    session = create_mock_session()
    repository = UserPreferenceRepository(
        session
    )

    await repository.add_favorite_state(
        user_id=uuid4(),
        state_code="IN-TG",
    )

    statement = session.execute.await_args.args[0]

    compiled_sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
        )
    )

    assert "ON CONFLICT" in compiled_sql
    assert "DO NOTHING" in compiled_sql


@pytest.mark.asyncio
async def test_favorite_state_query_joins_states(
) -> None:
    """Confirm favorite-state output uses state data."""

    session = create_mock_session()
    repository = UserPreferenceRepository(
        session
    )

    scalar_result = Mock()
    scalar_result.all.return_value = []

    session.scalars.return_value = scalar_result

    await repository.list_favorite_states(
        uuid4()
    )

    statement = session.scalars.await_args.args[0]

    compiled_sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
        )
    )

    assert "JOIN user_favorite_states" in (
        compiled_sql
    )
    assert "ORDER BY" in compiled_sql


def test_valid_top_ten_rankings() -> None:
    """Confirm a sequential ranking is accepted."""

    rankings = [
        StateRankingInput(
            article_id=uuid4(),
            rank_position=position,
            ranking_score=Decimal(
                str(100 - position)
            ),
        )
        for position in range(1, 11)
    ]

    validate_state_rankings(rankings)


@pytest.mark.parametrize(
    "rankings",
    [
        [
            StateRankingInput(
                article_id=uuid4(),
                rank_position=1,
                ranking_score=Decimal("10"),
            ),
            StateRankingInput(
                article_id=uuid4(),
                rank_position=1,
                ranking_score=Decimal("9"),
            ),
        ],
        [
            StateRankingInput(
                article_id=uuid4(),
                rank_position=2,
                ranking_score=Decimal("10"),
            )
        ],
        [
            StateRankingInput(
                article_id=uuid4(),
                rank_position=1,
                ranking_score=Decimal("-1"),
            )
        ],
    ],
)
def test_invalid_rankings_are_rejected(
    rankings: list[StateRankingInput],
) -> None:
    """Confirm malformed ranking lists fail."""

    with pytest.raises(ValueError):
        validate_state_rankings(rankings)


@pytest.mark.asyncio
async def test_replace_top_ten_creates_records(
) -> None:
    """Confirm a ranking snapshot is replaced."""

    session = create_mock_session()
    repository = StateRankingRepository(
        session
    )

    rankings = [
        StateRankingInput(
            article_id=uuid4(),
            rank_position=1,
            ranking_score=Decimal("95.50"),
            score_components={
                "freshness": 40,
                "relevance": 55.5,
            },
        ),
        StateRankingInput(
            article_id=uuid4(),
            rank_position=2,
            ranking_score=Decimal("90.25"),
        ),
    ]

    result = await repository.replace_top_ten(
        state_code="IN-TG",
        ranking_date=date(2026, 6, 27),
        rankings=rankings,
    )

    assert len(result) == 2
    assert result[0].state_code == "IN-TG"
    assert result[0].rank_position == 1
    assert result[1].rank_position == 2

    session.execute.assert_awaited_once()
    session.add_all.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_ranking_query_orders_by_position(
) -> None:
    """Confirm rankings are returned 1 through 10."""

    session = create_mock_session()
    repository = StateRankingRepository(
        session
    )

    scalar_result = Mock()
    scalar_result.all.return_value = []

    session.scalars.return_value = scalar_result

    await repository.list_rankings(
        state_code="IN-TG",
        ranking_date=date(2026, 6, 27),
    )

    statement = session.scalars.await_args.args[0]

    compiled_sql = str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={
                "literal_binds": True,
            },
        )
    )

    assert "state_news_rankings" in compiled_sql
    assert "rank_position ASC" in compiled_sql
    assert "LIMIT 10" in compiled_sql