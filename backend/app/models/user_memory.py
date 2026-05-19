from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class UserMemory(Base):
    __tablename__ = "user_memory"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    favorite_cuisines: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    taste_preference: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    avoid_foods: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    price_preference: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    favorite_dishes: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    preferred_scenes: Mapped[list[Any] | None] = mapped_column(JSONB, nullable=True)
    memory_summary: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    source_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped[User] = relationship(back_populates="memory")
