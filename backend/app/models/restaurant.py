from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.reviews import Review


class Restaurant(Base):
    """
    id：唯一标识餐厅
    poi_id：餐厅在POI数据源中的唯一标识
    name：餐厅名称
    address：餐厅地址
    photo：餐厅照片URL
    location：餐厅地理位置（经纬度等信息）
    cuisine_type：餐厅菜系类型
    rating：餐厅平均评分
    avg_price：餐厅平均价格
    raw_data：餐厅原始数据（存储从POI数据源获取的
    餐厅信息，便于后续数据分析和处理）
    created_at：餐厅记录创建时间
    updated_at：餐厅记录更新时间
    reviews：餐厅的用户评论列表
    """
    __tablename__ = "restaurants"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    poi_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    location: Mapped[dict[str, Any] | str | None] = mapped_column(JSONB, nullable=True)
    cuisine_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    rating: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_price: Mapped[int | None] = mapped_column(Integer, nullable=True)
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

    reviews: Mapped[list[Review]] = relationship(
        back_populates="restaurant",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
