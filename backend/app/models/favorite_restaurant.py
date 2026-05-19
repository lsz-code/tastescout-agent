from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.favorite_collection import FavoriteCollection
    from app.models.user import User


class FavoriteRestaurant(Base):
    __tablename__ = "favorite_restaurants"
    __table_args__ = (
        UniqueConstraint("user_id", "poi_id", name="uq_favorite_restaurants_user_poi"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    collection_id: Mapped[int] = mapped_column(
        ForeignKey("favorite_collections.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    poi_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    location: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    cuisine_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
    distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    recommended_dishes: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    review_summary: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    recommend_reason: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    raw_data: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    collection: Mapped[FavoriteCollection] = relationship(back_populates="restaurants")
    user: Mapped[User] = relationship(back_populates="favorite_restaurants")
