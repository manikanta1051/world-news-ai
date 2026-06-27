import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from src.database import (
    close_database_engine,
    get_async_engine,
)
from src.database.models import ArticleRecord
from src.database.repositories import (
    ArticleRepository,
    IndiaLocationRepository,
    NewsSourceRepository,
    StateRankingInput,
    StateRankingRepository,
    UserPreferenceRepository,
)


async def run_integration_test() -> None:
    """Test repositories against RDS and roll back test data."""

    engine = get_async_engine()
    connection = await engine.connect()
    transaction = await connection.begin()

    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
    )

    run_id = uuid4().hex[:12]

    try:
        location_repository = IndiaLocationRepository(
            session
        )
        source_repository = NewsSourceRepository(
            session
        )
        article_repository = ArticleRepository(
            session
        )
        preference_repository = UserPreferenceRepository(
            session
        )
        ranking_repository = StateRankingRepository(
            session
        )

        states = await location_repository.list_states()

        assert len(states) == 36

        source, source_created = (
            await source_repository.get_or_create(
                name=f"Integration Source {run_id}",
                source_type="integration_test",
                country_code="IN",
            )
        )

        article_url = (
            "https://example.com/integration/"
            f"{run_id}"
        )

        article = ArticleRecord(
            source_id=source.id,
            title="Repository integration test",
            description=(
                "Temporary article created during "
                "repository testing."
            ),
            url=article_url,
            published_at=datetime.now(timezone.utc),
            primary_category="Technology",
            language_code="en",
        )

        await article_repository.add(article)

        await article_repository.upsert_country_link(
            article_id=article.id,
            country_code="IN",
            relevance_score=Decimal("1.0000"),
        )

        await article_repository.upsert_state_link(
            article_id=article.id,
            state_code="IN-TG",
            relevance_score=Decimal("0.9500"),
            is_primary=True,
            detection_method="integration_test",
        )

        saved_article = await article_repository.get_by_url(
            article_url
        )

        assert saved_article is not None
        assert saved_article.id == article.id

        user, user_created = (
            await preference_repository.get_or_create_user(
                email=f"integration-{run_id}@example.com",
                display_name="Integration Test",
            )
        )

        favorite_countries = (
            await preference_repository
            .replace_favorite_countries(
                user_id=user.id,
                country_codes=["IN", "US"],
            )
        )

        await preference_repository.add_favorite_state(
            user_id=user.id,
            state_code="IN-TG",
        )

        favorite_states = (
            await preference_repository
            .list_favorite_states(user.id)
        )

        ranking_input = StateRankingInput(
            article_id=article.id,
            rank_position=1,
            ranking_score=Decimal("100.0000"),
            score_components={
                "integration_test": True,
            },
        )

        await ranking_repository.replace_top_ten(
            state_code="IN-TG",
            ranking_date=date.today(),
            rankings=[ranking_input],
        )

        rankings = await ranking_repository.list_rankings(
            state_code="IN-TG",
            ranking_date=date.today(),
        )

        assert len(favorite_countries) == 2
        assert any(
            state.code == "IN-TG"
            for state in favorite_states
        )
        assert len(rankings) == 1

        print("Repository integration test successful")
        print(f"India regions found: {len(states)}")
        print(f"Source created: {source_created}")
        print(f"Article ID: {article.id}")
        print(f"User created: {user_created}")
        print(
            f"Favorite countries: "
            f"{len(favorite_countries)}"
        )
        print(
            f"Favorite states: "
            f"{len(favorite_states)}"
        )
        print(f"Ranking records: {len(rankings)}")
        print("Temporary test data will be rolled back.")

    finally:
        await session.close()

        if transaction.is_active:
            await transaction.rollback()

        await connection.close()
        await close_database_engine()


if __name__ == "__main__":
    asyncio.run(run_integration_test())