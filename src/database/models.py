from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID as PythonUUID
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import (
    JSONB,
    UUID,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from src.database.base import (
    Base,
    TimestampMixin,
)


class NewsSourceRecord(
    TimestampMixin,
    Base,
):
    """Publisher or provider that supplied an article."""

    __tablename__ = "news_sources"

    id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    source_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    homepage_url: Mapped[str | None] = mapped_column(
        String(2048),
    )

    country_code: Mapped[str | None] = mapped_column(
        String(2),
    )

    credibility_score: Mapped[
        Decimal | None
    ] = mapped_column(
        Numeric(5, 2),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    extra_metadata: Mapped[dict[str, object]] = (
        mapped_column(
            JSONB,
            nullable=False,
            default=dict,
            server_default=text("'{}'::jsonb"),
        )
    )

    articles: Mapped[list[ArticleRecord]] = relationship(
        back_populates="source",
    )

    __table_args__ = (
        UniqueConstraint(
            "name",
            "source_type",
            name="uq_news_sources_name_type",
        ),
        CheckConstraint(
            (
                "credibility_score IS NULL OR "
                "(credibility_score >= 0 "
                "AND credibility_score <= 100)"
            ),
            name="credibility_score_range",
        ),
        CheckConstraint(
            (
                "country_code IS NULL OR "
                "length(country_code) = 2"
            ),
            name="country_code_length",
        ),
        Index(
            "ix_news_sources_country_code",
            "country_code",
        ),
    )


class IndianStateRecord(
    TimestampMixin,
    Base,
):
    """Indian state or Union Territory."""

    __tablename__ = "indian_states"

    code: Mapped[str] = mapped_column(
        String(8),
        primary_key=True,
    )

    short_code: Mapped[str] = mapped_column(
        String(3),
        nullable=False,
        unique=True,
    )

    name: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
        unique=True,
    )

    region_type: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        nullable=False,
        default="IN",
        server_default=text("'IN'"),
    )

    capital: Mapped[str | None] = mapped_column(
        String(120),
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    districts: Mapped[list[DistrictRecord]] = relationship(
        back_populates="state",
        cascade="all, delete-orphan",
    )

    cities: Mapped[list[CityRecord]] = relationship(
        back_populates="state",
        cascade="all, delete-orphan",
    )

    article_links: Mapped[
        list[ArticleStateRecord]
    ] = relationship(
        back_populates="state",
    )

    favorite_links: Mapped[
        list[UserFavoriteStateRecord]
    ] = relationship(
        back_populates="state",
    )

    rankings: Mapped[
        list[StateNewsRankingRecord]
    ] = relationship(
        back_populates="state",
    )

    __table_args__ = (
        CheckConstraint(
            (
                "region_type IN "
                "('state', 'union_territory')"
            ),
            name="region_type_values",
        ),
        CheckConstraint(
            "country_code = 'IN'",
            name="country_code_india",
        ),
        CheckConstraint(
            "display_order > 0",
            name="display_order_positive",
        ),
    )


class DistrictRecord(
    TimestampMixin,
    Base,
):
    """District belonging to an Indian state or territory."""

    __tablename__ = "districts"

    id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    state_code: Mapped[str] = mapped_column(
        ForeignKey(
            "indian_states.code",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    state: Mapped[IndianStateRecord] = relationship(
        back_populates="districts",
    )

    cities: Mapped[list[CityRecord]] = relationship(
        back_populates="district",
    )

    article_links: Mapped[
        list[ArticleDistrictRecord]
    ] = relationship(
        back_populates="district",
    )

    __table_args__ = (
        UniqueConstraint(
            "state_code",
            "name",
            name="uq_districts_state_name",
        ),
        UniqueConstraint(
            "state_code",
            "slug",
            name="uq_districts_state_slug",
        ),
        Index(
            "ix_districts_state_code",
            "state_code",
        ),
    )


class CityRecord(
    TimestampMixin,
    Base,
):
    """City or major locality inside an Indian state."""

    __tablename__ = "cities"

    id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    state_code: Mapped[str] = mapped_column(
        ForeignKey(
            "indian_states.code",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    district_id: Mapped[
        PythonUUID | None
    ] = mapped_column(
        ForeignKey(
            "districts.id",
            ondelete="SET NULL",
        ),
    )

    name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    slug: Mapped[str] = mapped_column(
        String(180),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    state: Mapped[IndianStateRecord] = relationship(
        back_populates="cities",
    )

    district: Mapped[
        DistrictRecord | None
    ] = relationship(
        back_populates="cities",
    )

    article_links: Mapped[
        list[ArticleCityRecord]
    ] = relationship(
        back_populates="city",
    )

    __table_args__ = (
        UniqueConstraint(
            "state_code",
            "name",
            name="uq_cities_state_name",
        ),
        UniqueConstraint(
            "state_code",
            "slug",
            name="uq_cities_state_slug",
        ),
        Index(
            "ix_cities_state_code",
            "state_code",
        ),
        Index(
            "ix_cities_district_id",
            "district_id",
        ),
    )


class ArticleRecord(
    TimestampMixin,
    Base,
):
    """Validated news article stored in PostgreSQL."""

    __tablename__ = "articles"

    id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    source_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey(
            "news_sources.id",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
    )

    content: Mapped[str | None] = mapped_column(
        Text,
    )

    summary: Mapped[str | None] = mapped_column(
        Text,
    )

    url: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        unique=True,
    )

    canonical_url: Mapped[str | None] = mapped_column(
        String(2048),
        unique=True,
    )

    image_url: Mapped[str | None] = mapped_column(
        String(2048),
    )

    author: Mapped[str | None] = mapped_column(
        String(200),
    )

    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )

    collected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    primary_category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="General",
        server_default=text("'General'"),
    )

    sentiment: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="Unknown",
        server_default=text("'Unknown'"),
    )

    language_code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        default="en",
        server_default=text("'en'"),
    )

    ai_processed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        unique=True,
    )

    keywords: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    share_caption: Mapped[str | None] = mapped_column(
        Text,
    )

    social_card_data: Mapped[
        dict[str, object]
    ] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    raw_s3_uri: Mapped[str | None] = mapped_column(
        String(2048),
    )

    processed_s3_uri: Mapped[
        str | None
    ] = mapped_column(
        String(2048),
    )

    source: Mapped[NewsSourceRecord] = relationship(
        back_populates="articles",
    )

    labels: Mapped[
        list[ArticleLabelRecord]
    ] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )

    countries: Mapped[
        list[ArticleCountryRecord]
    ] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )

    states: Mapped[
        list[ArticleStateRecord]
    ] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )

    districts: Mapped[
        list[ArticleDistrictRecord]
    ] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )

    cities: Mapped[
        list[ArticleCityRecord]
    ] = relationship(
        back_populates="article",
        cascade="all, delete-orphan",
    )

    rankings: Mapped[
        list[StateNewsRankingRecord]
    ] = relationship(
        back_populates="article",
    )

    __table_args__ = (
        CheckConstraint(
            "length(language_code) BETWEEN 2 AND 10",
            name="language_code_length",
        ),
        CheckConstraint(
            (
                "content_hash IS NULL OR "
                "content_hash ~ '^[A-Fa-f0-9]{64}$'"
            ),
            name="content_hash_format",
        ),
        Index(
            "ix_articles_source_id",
            "source_id",
        ),
        Index(
            "ix_articles_published_at",
            "published_at",
        ),
        Index(
            "ix_articles_primary_category",
            "primary_category",
        ),
        Index(
            "ix_articles_language_code",
            "language_code",
        ),
        Index(
            "ix_articles_ai_processed",
            "ai_processed",
        ),
    )


class ArticleLabelRecord(Base):
    """Dynamic label assigned to an article."""

    __tablename__ = "article_labels"

    article_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey(
            "articles.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    label: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    article: Mapped[ArticleRecord] = relationship(
        back_populates="labels",
    )


class ArticleCountryRecord(Base):
    """Country associated with an article's subject."""

    __tablename__ = "article_countries"

    article_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey(
            "articles.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        primary_key=True,
    )

    relevance_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        default=Decimal("1.0000"),
        server_default=text("1.0000"),
    )

    article: Mapped[ArticleRecord] = relationship(
        back_populates="countries",
    )

    __table_args__ = (
        CheckConstraint(
            "length(country_code) = 2",
            name="country_code_length",
        ),
        CheckConstraint(
            (
                "relevance_score >= 0 "
                "AND relevance_score <= 1"
            ),
            name="relevance_score_range",
        ),
    )


class ArticleStateRecord(Base):
    """Relationship between an article and an Indian state."""

    __tablename__ = "article_states"

    article_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey(
            "articles.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    state_code: Mapped[str] = mapped_column(
        ForeignKey(
            "indian_states.code",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )

    relevance_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    detection_method: Mapped[str | None] = mapped_column(
        String(50),
    )

    article: Mapped[ArticleRecord] = relationship(
        back_populates="states",
    )

    state: Mapped[IndianStateRecord] = relationship(
        back_populates="article_links",
    )

    __table_args__ = (
        CheckConstraint(
            (
                "relevance_score >= 0 "
                "AND relevance_score <= 1"
            ),
            name="relevance_score_range",
        ),
        Index(
            "ix_article_states_state_score",
            "state_code",
            "relevance_score",
        ),
    )


class ArticleDistrictRecord(Base):
    """Relationship between an article and a district."""

    __tablename__ = "article_districts"

    article_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey(
            "articles.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    district_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey(
            "districts.id",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )

    relevance_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    article: Mapped[ArticleRecord] = relationship(
        back_populates="districts",
    )

    district: Mapped[DistrictRecord] = relationship(
        back_populates="article_links",
    )

    __table_args__ = (
        CheckConstraint(
            (
                "relevance_score >= 0 "
                "AND relevance_score <= 1"
            ),
            name="relevance_score_range",
        ),
    )


class ArticleCityRecord(Base):
    """Relationship between an article and a city."""

    __tablename__ = "article_cities"

    article_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey(
            "articles.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    city_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey(
            "cities.id",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )

    relevance_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
    )

    article: Mapped[ArticleRecord] = relationship(
        back_populates="cities",
    )

    city: Mapped[CityRecord] = relationship(
        back_populates="article_links",
    )

    __table_args__ = (
        CheckConstraint(
            (
                "relevance_score >= 0 "
                "AND relevance_score <= 1"
            ),
            name="relevance_score_range",
        ),
    )


class AppUserRecord(
    TimestampMixin,
    Base,
):
    """World News AI application user."""

    __tablename__ = "app_users"

    id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
        unique=True,
    )

    display_name: Mapped[str | None] = mapped_column(
        String(150),
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=text("true"),
    )

    favorite_countries: Mapped[
        list[UserFavoriteCountryRecord]
    ] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    favorite_states: Mapped[
        list[UserFavoriteStateRecord]
    ] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )


class UserFavoriteCountryRecord(Base):
    """One of a user's maximum two favorite countries."""

    __tablename__ = "user_favorite_countries"

    user_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey(
            "app_users.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    country_code: Mapped[str] = mapped_column(
        String(2),
        primary_key=True,
    )

    priority: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[AppUserRecord] = relationship(
        back_populates="favorite_countries",
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "priority",
            name=(
                "uq_user_favorite_countries_"
                "user_priority"
            ),
        ),
        CheckConstraint(
            "priority BETWEEN 1 AND 2",
            name="favorite_country_priority_range",
        ),
        CheckConstraint(
            "length(country_code) = 2",
            name="country_code_length",
        ),
    )


class UserFavoriteStateRecord(Base):
    """Indian state selected by an application user."""

    __tablename__ = "user_favorite_states"

    user_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey(
            "app_users.id",
            ondelete="CASCADE",
        ),
        primary_key=True,
    )

    state_code: Mapped[str] = mapped_column(
        ForeignKey(
            "indian_states.code",
            ondelete="RESTRICT",
        ),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped[AppUserRecord] = relationship(
        back_populates="favorite_states",
    )

    state: Mapped[IndianStateRecord] = relationship(
        back_populates="favorite_links",
    )


class StateNewsRankingRecord(Base):
    """Top 10 article ranking for an Indian state."""

    __tablename__ = "state_news_rankings"

    id: Mapped[PythonUUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
    )

    state_code: Mapped[str] = mapped_column(
        ForeignKey(
            "indian_states.code",
            ondelete="RESTRICT",
        ),
        nullable=False,
    )

    article_id: Mapped[PythonUUID] = mapped_column(
        ForeignKey(
            "articles.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    ranking_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    ranking_window: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="24h",
        server_default=text("'24h'"),
    )

    category_filter: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        default="all",
        server_default=text("'all'"),
    )

    rank_position: Mapped[int] = mapped_column(
        SmallInteger,
        nullable=False,
    )

    ranking_score: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
    )

    score_components: Mapped[
        dict[str, object]
    ] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    state: Mapped[IndianStateRecord] = relationship(
        back_populates="rankings",
    )

    article: Mapped[ArticleRecord] = relationship(
        back_populates="rankings",
    )

    __table_args__ = (
        UniqueConstraint(
            "state_code",
            "ranking_date",
            "ranking_window",
            "category_filter",
            "rank_position",
            name="uq_state_rankings_position",
        ),
        UniqueConstraint(
            "state_code",
            "ranking_date",
            "ranking_window",
            "category_filter",
            "article_id",
            name="uq_state_rankings_article",
        ),
        CheckConstraint(
            "rank_position BETWEEN 1 AND 10",
            name="rank_position_top_ten",
        ),
        CheckConstraint(
            "ranking_score >= 0",
            name="ranking_score_nonnegative",
        ),
        Index(
            "ix_state_rankings_lookup",
            "state_code",
            "ranking_date",
            "ranking_window",
            "category_filter",
        ),
    )