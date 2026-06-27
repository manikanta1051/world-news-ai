from sqlalchemy import (
    CheckConstraint,
    UniqueConstraint,
)
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from src.database import (
    Base,
    INDIA_STATE_AND_UT_SEED,
)


EXPECTED_TABLES = {
    "news_sources",
    "indian_states",
    "districts",
    "cities",
    "articles",
    "article_labels",
    "article_countries",
    "article_states",
    "article_districts",
    "article_cities",
    "app_users",
    "user_favorite_countries",
    "user_favorite_states",
    "state_news_rankings",
}


def test_expected_database_tables_exist() -> None:
    """Confirm that all planned tables are registered."""

    assert set(Base.metadata.tables) == EXPECTED_TABLES


def test_articles_table_has_required_columns() -> None:
    """Confirm core article fields exist."""

    article_table = Base.metadata.tables["articles"]

    required_columns = {
        "id",
        "source_id",
        "title",
        "url",
        "published_at",
        "primary_category",
        "language_code",
        "content_hash",
        "raw_s3_uri",
        "processed_s3_uri",
    }

    assert required_columns.issubset(
        set(article_table.columns.keys())
    )


def test_location_mapping_tables_exist() -> None:
    """Confirm state, district, and city mappings exist."""

    assert "article_states" in Base.metadata.tables
    assert "article_districts" in Base.metadata.tables
    assert "article_cities" in Base.metadata.tables

    state_table = Base.metadata.tables[
        "article_states"
    ]

    assert {
        "article_id",
        "state_code",
        "relevance_score",
        "is_primary",
        "detection_method",
    }.issubset(
        set(state_table.columns.keys())
    )


def test_india_seed_has_expected_counts() -> None:
    """Confirm 28 states and 8 territories are present."""

    state_count = sum(
        1
        for region in INDIA_STATE_AND_UT_SEED
        if region["region_type"] == "state"
    )

    territory_count = sum(
        1
        for region in INDIA_STATE_AND_UT_SEED
        if region["region_type"]
        == "union_territory"
    )

    assert len(INDIA_STATE_AND_UT_SEED) == 36
    assert state_count == 28
    assert territory_count == 8


def test_india_seed_values_are_unique() -> None:
    """Confirm codes and names are not repeated."""

    codes = [
        region["code"]
        for region in INDIA_STATE_AND_UT_SEED
    ]

    short_codes = [
        region["short_code"]
        for region in INDIA_STATE_AND_UT_SEED
    ]

    names = [
        region["name"]
        for region in INDIA_STATE_AND_UT_SEED
    ]

    assert len(codes) == len(set(codes))
    assert len(short_codes) == len(
        set(short_codes)
    )
    assert len(names) == len(set(names))


def test_favorite_country_schema_limits_priorities() -> None:
    """Confirm favorite countries support only slots one and two."""

    table = Base.metadata.tables[
        "user_favorite_countries"
    ]

    checks = [
        constraint
        for constraint in table.constraints
        if isinstance(
            constraint,
            CheckConstraint,
        )
    ]

    unique_constraints = [
        constraint
        for constraint in table.constraints
        if isinstance(
            constraint,
            UniqueConstraint,
        )
    ]

    assert any(
        "priority BETWEEN 1 AND 2"
        in str(constraint.sqltext)
        for constraint in checks
    )

    assert any(
        set(constraint.columns.keys())
        == {"user_id", "priority"}
        for constraint in unique_constraints
    )


def test_state_ranking_schema_supports_top_ten() -> None:
    """Confirm rankings are restricted to positions 1–10."""

    table = Base.metadata.tables[
        "state_news_rankings"
    ]

    checks = [
        constraint
        for constraint in table.constraints
        if isinstance(
            constraint,
            CheckConstraint,
        )
    ]

    assert any(
        "rank_position BETWEEN 1 AND 10"
        in str(constraint.sqltext)
        for constraint in checks
    )

    assert {
        "state_code",
        "article_id",
        "ranking_date",
        "ranking_window",
        "category_filter",
        "rank_position",
        "ranking_score",
        "score_components",
    }.issubset(
        set(table.columns.keys())
    )


def test_all_tables_compile_for_postgresql() -> None:
    """Confirm every model produces PostgreSQL DDL."""

    dialect = postgresql.dialect()

    for table in Base.metadata.sorted_tables:
        ddl = str(
            CreateTable(table).compile(
                dialect=dialect
            )
        )

        assert "CREATE TABLE" in ddl
        assert table.name in ddl