from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    AppUserRecord,
    IndianStateRecord,
    UserFavoriteCountryRecord,
    UserFavoriteStateRecord,
)


def normalize_country_codes(
    country_codes: Sequence[str],
) -> tuple[str, ...]:
    """Validate and normalize favorite-country codes."""

    normalized_codes = tuple(
        code.strip().upper()
        for code in country_codes
    )

    if len(normalized_codes) > 2:
        raise ValueError(
            "A user can select a maximum "
            "of two favorite countries."
        )

    if len(normalized_codes) != len(
        set(normalized_codes)
    ):
        raise ValueError(
            "Favorite countries cannot contain "
            "duplicate country codes."
        )

    for country_code in normalized_codes:
        if (
            len(country_code) != 2
            or not country_code.isalpha()
        ):
            raise ValueError(
                "Country codes must contain exactly "
                "two letters."
            )

    return normalized_codes


class UserPreferenceRepository:
    """Database operations for users and preferences."""

    def __init__(
        self,
        session: AsyncSession,
    ) -> None:
        self.session = session

    async def get_user_by_id(
        self,
        user_id: UUID,
    ) -> AppUserRecord | None:
        """Return an application user by ID."""

        return await self.session.get(
            AppUserRecord,
            user_id,
        )

    async def get_user_by_email(
        self,
        email: str,
    ) -> AppUserRecord | None:
        """Return an application user by email."""

        statement = select(AppUserRecord).where(
            AppUserRecord.email == email.strip().lower()
        )

        result = await self.session.scalars(statement)

        return result.first()

    async def get_or_create_user(
        self,
        *,
        email: str,
        display_name: str | None = None,
    ) -> tuple[AppUserRecord, bool]:
        """Return an existing user or create one."""

        normalized_email = email.strip().lower()

        if not normalized_email:
            raise ValueError(
                "User email cannot be empty."
            )

        existing_user = await self.get_user_by_email(
            normalized_email
        )

        if existing_user is not None:
            return existing_user, False

        new_user = AppUserRecord(
            email=normalized_email,
            display_name=display_name,
        )

        self.session.add(new_user)
        await self.session.flush()

        return new_user, True

    async def replace_favorite_countries(
        self,
        *,
        user_id: UUID,
        country_codes: Sequence[str],
    ) -> Sequence[UserFavoriteCountryRecord]:
        """Replace a user's maximum two countries."""

        normalized_codes = normalize_country_codes(
            country_codes
        )

        delete_statement = delete(
            UserFavoriteCountryRecord
        ).where(
            UserFavoriteCountryRecord.user_id
            == user_id
        )

        await self.session.execute(
            delete_statement
        )

        favorite_records = [
            UserFavoriteCountryRecord(
                user_id=user_id,
                country_code=country_code,
                priority=priority,
            )
            for priority, country_code in enumerate(
                normalized_codes,
                start=1,
            )
        ]

        if favorite_records:
            self.session.add_all(
                favorite_records
            )

        await self.session.flush()

        return favorite_records

    async def list_favorite_countries(
        self,
        user_id: UUID,
    ) -> Sequence[UserFavoriteCountryRecord]:
        """Return favorite countries in priority order."""

        statement = (
            select(UserFavoriteCountryRecord)
            .where(
                UserFavoriteCountryRecord.user_id
                == user_id
            )
            .order_by(
                UserFavoriteCountryRecord
                .priority
                .asc()
            )
        )

        result = await self.session.scalars(statement)

        return result.all()

    async def add_favorite_state(
        self,
        *,
        user_id: UUID,
        state_code: str,
    ) -> None:
        """Add a favorite state without duplicates."""

        statement = insert(
            UserFavoriteStateRecord
        ).values(
            user_id=user_id,
            state_code=state_code,
        )

        statement = statement.on_conflict_do_nothing(
            index_elements=[
                UserFavoriteStateRecord.user_id,
                UserFavoriteStateRecord.state_code,
            ]
        )

        await self.session.execute(statement)

    async def remove_favorite_state(
        self,
        *,
        user_id: UUID,
        state_code: str,
    ) -> bool:
        """Remove a favorite Indian state."""

        statement = delete(
            UserFavoriteStateRecord
        ).where(
            UserFavoriteStateRecord.user_id
            == user_id,
            UserFavoriteStateRecord.state_code
            == state_code,
        )

        result = await self.session.execute(
            statement
        )

        return bool(result.rowcount)

    async def list_favorite_states(
        self,
        user_id: UUID,
    ) -> Sequence[IndianStateRecord]:
        """Return the user's favorite state records."""

        statement = (
            select(IndianStateRecord)
            .join(
                UserFavoriteStateRecord,
                UserFavoriteStateRecord.state_code
                == IndianStateRecord.code,
            )
            .where(
                UserFavoriteStateRecord.user_id
                == user_id,
                IndianStateRecord.is_active.is_(True),
            )
            .order_by(
                IndianStateRecord.display_order.asc()
            )
        )

        result = await self.session.scalars(statement)

        return result.all()