from typing import Any

import redis.asyncio as redis
from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import settings
from app.db.session import AsyncSessionLocal


router = APIRouter(prefix="/health", tags=["Health"])

#检查PostgreSQL数据库连接是否正常
async def check_postgres() -> dict[str, str | None]:
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(text("SELECT 1"))
            value = result.scalar_one()

        return {
            "component": "postgres",
            "status": "ok",
            "value": value,
            "error": None,
        }

    except Exception as e:
        return {
            "component": "postgres",
            "status": "failed",
            "error": repr(e),
        }

#检查Redis连接是否正常
async def check_redis() -> dict[str, str | None]:
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await client.ping()
        return {"status": "ok", "error": None}
    except Exception as exc:
        return {"status": "failed", "error": str(exc)}
    finally:
        await client.aclose()

#软件组件自检
@router.get("")
async def health_check() -> dict[str, Any]:
    components = {
        "postgres": await check_postgres(),
        "redis": await check_redis(),
    }
    status = (
        "ok"
        if all(component["status"] == "ok" for component in components.values())
        else "degraded"
    )

    return {
        "service": "TasteScout Agent Backend",
        "status": status,
        "components": components,
    }
