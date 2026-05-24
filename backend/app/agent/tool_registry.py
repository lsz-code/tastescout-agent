from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.short_term import ShortTermMemory
from app.skills.favorite import AddFavoriteByRankSkill, ShowFavoritesSkill
from app.skills.memory import GetUserMemorySkill, RefreshUserMemorySkill
from app.skills.registry import SkillRegistry
from app.skills.restaurant_search import RestaurantSearchSkill


def _build_registry() -> SkillRegistry:
    return SkillRegistry(
        [
            RestaurantSearchSkill(),
            AddFavoriteByRankSkill(),
            ShowFavoritesSkill(),
            GetUserMemorySkill(),
            RefreshUserMemorySkill(),
        ]
    )


_registry = _build_registry()


def openai_tool_definitions() -> list[dict[str, Any]]:
    return _registry.openai_tool_definitions()


def prepare_arguments(
    tool_name: str,
    arguments: dict[str, Any],
    state: dict[str, Any],
) -> dict[str, Any]:
    return _registry.prepare_arguments(tool_name, arguments, state)


def build_data(
    tool_name: str,
    result: dict[str, Any] | None,
) -> dict[str, Any] | None:
    return _registry.build_data(tool_name, result)


def build_template_reply(
    tool_name: str | None,
    result: dict[str, Any] | None,
    error: str | None,
) -> str | None:
    return _registry.build_template_reply(tool_name, result, error)


def extract_slots(
    tool_name: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    return _registry.extract_slots(tool_name, state)


def check_slots(
    tool_name: str,
    state: dict[str, Any],
) -> dict[str, Any]:
    return _registry.check_slots(tool_name, state)


async def ask_followup(
    tool_name: str,
    state: dict[str, Any],
    short_term_memory: ShortTermMemory,
) -> dict[str, Any]:
    return await _registry.ask_followup(tool_name, state, short_term_memory)

async def execute_tool(
    tool_name: str,
    db: AsyncSession,
    short_term_memory: ShortTermMemory,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    return await _registry.execute_tool(
        tool_name=tool_name,
        db=db,
        short_term_memory=short_term_memory,
        arguments=arguments,
    )
