from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.restaurant import Restaurant
    from app.models.user import User


class Review(Base):
    """
    id：唯一标识评论
    restaurant_id：评论所属餐厅的ID
    user_id：评论所属用户的ID
    content：评论内容
    rating：评论评分（可选）
    created_at：评论创建时间
    updated_at：评论更新时间
    restaurant：评论所属餐厅对象
    user：评论所属用户对象
    """

    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("restaurant_id", "user_id", name="uq_reviews_restaurant_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    restaurant_id: Mapped[int] = mapped_column(
        ForeignKey("restaurants.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    content: Mapped[str] = mapped_column(String(2000))
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    restaurant: Mapped[Restaurant] = relationship(back_populates="reviews")
    user: Mapped[User] = relationship(back_populates="reviews")
