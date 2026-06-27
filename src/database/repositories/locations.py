from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    CityRecord,
    DistrictRecord,
    IndianStateRecord,
)
from src.database.repositories.validators import (
    validate_result_limit,
)


VALID_REGION_TYPES = {
    "state",
    "union_territory",
}


class IndiaLocationRepository:
    """Database operations for Indian locations."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_state_by_code(
        self,
        state_code: str,
    ) -> IndianStateRecord | None:
        """Return an Indian state or territory by code."""

        return await self.session.get(
            IndianStateRecord,
            state_code,
        )

    async def list_states(
        self,
        *,
        region_type: str | None = None,
        active_only: bool = True,
    ) -> Sequence[IndianStateRecord]:
        """Return states and territories in display order."""

        if (
            region_type is not None
            and region_type not in VALID_REGION_TYPES
        ):
            raise ValueError(
                "Region type must be 'state' "
                "or 'union_territory'."
            )

        statement = select(IndianStateRecord)

        if active_only:
            statement = statement.where(
                IndianStateRecord.is_active.is_(True)
            )

        if region_type is not None:
            statement = statement.where(
                IndianStateRecord.region_type
                == region_type
            )

        statement = statement.order_by(
            IndianStateRecord.display_order.asc()
        )

        result = await self.session.scalars(statement)

        return result.all()

    async def get_district_by_id(
        self,
        district_id: UUID,
    ) -> DistrictRecord | None:
        """Return a district by primary key."""

        return await self.session.get(
            DistrictRecord,
            district_id,
        )

    async def list_districts(
        self,
        state_code: str,
        *,
        limit: int = 200,
    ) -> Sequence[DistrictRecord]:
        """Return districts belonging to a state."""

        validate_result_limit(limit)

        statement = (
            select(DistrictRecord)
            .where(
                DistrictRecord.state_code
                == state_code,
                DistrictRecord.is_active.is_(True),
            )
            .order_by(DistrictRecord.name.asc())
            .limit(limit)
        )

        result = await self.session.scalars(statement)

        return result.all()

    async def get_city_by_id(
        self,
        city_id: UUID,
    ) -> CityRecord | None:
        """Return a city by primary key."""

        return await self.session.get(
            CityRecord,
            city_id,
        )

    async def list_cities(
        self,
        state_code: str,
        *,
        district_id: UUID | None = None,
        limit: int = 200,
    ) -> Sequence[CityRecord]:
        """Return cities belonging to a state or district."""

        validate_result_limit(limit)

        statement = select(CityRecord).where(
            CityRecord.state_code == state_code,
            CityRecord.is_active.is_(True),
        )

        if district_id is not None:
            statement = statement.where(
                CityRecord.district_id == district_id
            )

        statement = (
            statement
            .order_by(CityRecord.name.asc())
            .limit(limit)
        )

        result = await self.session.scalars(statement)

        return result.all()
