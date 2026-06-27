import asyncio

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert

from src.database.connection import (
    close_database_engine,
    get_async_engine,
)
from src.database.india_seed import (
    INDIA_STATE_AND_UT_SEED,
)
from src.database.models import IndianStateRecord


async def seed_india_regions() -> None:
    """Insert or update all Indian states and territories."""

    rows = [
        {
            "code": region["code"],
            "short_code": region["short_code"],
            "name": region["name"],
            "region_type": region["region_type"],
            "country_code": "IN",
            "display_order": region["display_order"],
            "is_active": True,
        }
        for region in INDIA_STATE_AND_UT_SEED
    ]

    table = IndianStateRecord.__table__

    statement = insert(table).values(rows)

    statement = statement.on_conflict_do_update(
        index_elements=[table.c.code],
        set_={
            "short_code": statement.excluded.short_code,
            "name": statement.excluded.name,
            "region_type": statement.excluded.region_type,
            "country_code": statement.excluded.country_code,
            "display_order": statement.excluded.display_order,
            "is_active": statement.excluded.is_active,
            "updated_at": func.now(),
        },
    )

    engine = get_async_engine()

    try:
        async with engine.begin() as connection:
            await connection.execute(statement)

            result = await connection.execute(
                text(
                    """
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (
                            WHERE is_active = true
                        ) AS active,
                        COUNT(*) FILTER (
                            WHERE region_type = 'state'
                        ) AS states,
                        COUNT(*) FILTER (
                            WHERE region_type = 'union_territory'
                        ) AS territories
                    FROM indian_states
                    """
                )
            )

            counts = result.mappings().one()

        print("India region seed completed")
        print(f"Total regions: {counts['total']}")
        print(f"Active regions: {counts['active']}")
        print(f"States: {counts['states']}")
        print(
            "Union Territories: "
            f"{counts['territories']}"
        )

        if counts["total"] != 36:
            raise RuntimeError(
                "Expected 36 India regions after seeding."
            )

        if counts["states"] != 28:
            raise RuntimeError(
                "Expected 28 Indian states."
            )

        if counts["territories"] != 8:
            raise RuntimeError(
                "Expected 8 Union Territories."
            )

    finally:
        await close_database_engine()


if __name__ == "__main__":
    asyncio.run(seed_india_regions())