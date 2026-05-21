from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.favorite_collection import FavoriteCollection
    from app.models.favorite_restaurant import FavoriteRestaurant
    from app.models.reviews import Review
    from app.models.session import Session
    from app.models.user_memory import UserMemory


class User(Base):
    """
    id:唯一标识用户
    user_id:用户在认证系统中的唯一标识
    username:用户名
    avatar_url:用户头像URL
    created_at:用户记录创建时间
    updated_at:用户记录更新时间
    favorite_collections:用户的收藏夹列表
    favorite_restaurants:用户收藏的餐厅列表
    memory:用户的记忆信息
    sessions:用户的会话列表
    reviews:用户的评论列表
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(100), nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    favorite_collections: Mapped[list[FavoriteCollection]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    favorite_restaurants: Mapped[list[FavoriteRestaurant]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    memory: Mapped[UserMemory | None] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
        uselist=False,
    )
    sessions: Mapped[list[Session]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    reviews: Mapped[list[Review]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
