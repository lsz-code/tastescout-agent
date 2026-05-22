from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.short_term import ShortTermMemory
from app.services.memory_service import MemoryService
from app.skills.base import Skill


class GetUserMemorySkill(Skill):
    name = "get_user_memory"
    description = "查看用户长期饮食偏好 Memory。"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
        },
        "required": ["user_id"],
    }

    async def run(
        self,
        db: AsyncSession,
        short_term_memory: ShortTermMemory,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        service = MemoryService(db)
        response = await service.get_long_term_memory(arguments["user_id"])
        return response.model_dump(mode="json")
    
    def build_data(
        self,
        result: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if result is None:
            return None
        return {"memory": result.get("memory") or result}
    
    def build_template_reply(
        self,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> str | None:
        if error:
            return f"操作失败：{error}"
        return "这是我当前记录的你的口味偏好。"


class RefreshUserMemorySkill(Skill):
    name = "refresh_user_memory"
    description = "根据收藏夹刷新用户长期 Memory。"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
        },
        "required": ["user_id"],
    }

    async def run(
        self,
        db: AsyncSession,
        short_term_memory: ShortTermMemory,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        service = MemoryService(db)
        response = await service.refresh_long_term_memory(arguments["user_id"])
        return response.model_dump(mode="json")
    
    def build_data(
        self,
        result: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if result is None:
            return None
        return {"memory": result.get("memory") or result}
    
    def build_template_reply(
        self,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> str | None:
        if error:
            return f"操作失败：{error}"
        return "已根据你的收藏刷新长期口味偏好。"