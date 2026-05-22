from typing import Any, Awaitable, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.short_term import ShortTermMemory
from app.schemas.favorite import AddFavoriteRestaurantRequest
from app.schemas.restaurant import RestaurantSearchFilters, RestaurantSearchRequest
from app.schemas.restaurant import Location as RestaurantLocation
from app.services.favorite_service import FavoriteService
from app.services.memory_service import MemoryService
from app.services.restaurant_search_service import RestaurantSearchService


ToolHandler = Callable[
    [AsyncSession, ShortTermMemory, dict[str, Any]],
    Awaitable[dict[str, Any]],
]


async def search_restaurants_handler(
    db: AsyncSession,
    short_term_memory: ShortTermMemory,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    filters = arguments.get("filters")
    payload = RestaurantSearchRequest(
        user_id=arguments["user_id"],
        session_id=arguments["session_id"],
        address=arguments.get("address"),
        location=(
            RestaurantLocation(**arguments["location"])
            if isinstance(arguments.get("location"), dict)
            else None
        ),
        city=arguments.get("city"),
        keyword=arguments.get("keyword") or "美食",
        radius=arguments.get("radius") or 3000,
        limit=arguments.get("limit") or 5,
        filters=RestaurantSearchFilters(**filters) if isinstance(filters, dict) else None,
    )
    service = RestaurantSearchService(db=db, short_term_memory=short_term_memory)
    response = await service.search(payload)
    return response.model_dump(mode="json")


async def add_favorite_by_rank_handler(
    db: AsyncSession,
    short_term_memory: ShortTermMemory,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    session_id = arguments["session_id"]
    rank = int(arguments["rank"])

    memory = await short_term_memory.get(session_id)
    candidates = memory.get("current_candidates")
    if not isinstance(candidates, list):
        raise ValueError("当前会话没有可收藏的餐厅候选，请先搜索餐厅。")

    restaurant = next(
        (
            item
            for item in candidates
            if isinstance(item, dict) and int(item.get("rank") or 0) == rank
        ),
        None,
    )
    if restaurant is None:
        raise ValueError(f"没有找到第 {rank} 家餐厅，请先重新搜索。")

    payload = AddFavoriteRestaurantRequest(
        user_id=arguments["user_id"],
        collection_id=arguments.get("collection_id"),
        poi_id=restaurant["poi_id"],
        name=restaurant["name"],
        address=restaurant.get("address"),
        photo=restaurant.get("photo"),
        location=restaurant.get("location"),
        cuisine_type=restaurant.get("cuisine_type"),
        rating=restaurant.get("rating"),
        avg_price=restaurant.get("avg_price"),
        distance=restaurant.get("distance"),
        recommended_dishes=restaurant.get("recommended_dishes"),
        review_summary=restaurant.get("review_summary"),
        recommend_reason=restaurant.get("recommend_reason"),
        raw_data=restaurant.get("raw_data"),
    )

    service = FavoriteService(db)
    response = await service.add_favorite(payload)
    result = response.model_dump(mode="json")
    result["restaurant"] = restaurant
    result["rank"] = rank
    return result


async def show_favorites_handler(
    db: AsyncSession,
    short_term_memory: ShortTermMemory,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    service = FavoriteService(db)
    favorites = await service.list_favorites(arguments["user_id"])
    return {
        "favorites": [item.model_dump(mode="json") for item in favorites],
    }


async def get_user_memory_handler(
    db: AsyncSession,
    short_term_memory: ShortTermMemory,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    service = MemoryService(db)
    response = await service.get_long_term_memory(arguments["user_id"])
    return response.model_dump(mode="json")


async def refresh_user_memory_handler(
    db: AsyncSession,
    short_term_memory: ShortTermMemory,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    service = MemoryService(db)
    response = await service.refresh_long_term_memory(arguments["user_id"])
    return response.model_dump(mode="json")


TOOLS: dict[str, dict[str, Any]] = {
    "search_restaurants": {
        "description": "按用户位置、地址、店名、关键词和偏好搜索餐厅。菜系不是必填项；没有关键词时默认搜索美食。用户找具体店名时，把店名放入 keyword，不要强制填 cuisine。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "session_id": {"type": "string"},
                "address": {"type": "string"},
                "location": {
                    "type": "object",
                    "properties": {
                        "longitude": {"type": "number"},
                        "latitude": {"type": "number"},
                    },
                },
                "city": {"type": "string"},
                "keyword": {"type": "string"},
                "radius": {"type": "integer", "default": 3000},
                "limit": {"type": "integer", "default": 5},
                "filters": {"type": "object"},
            },
            "required": ["user_id", "session_id"],
        },
        "handler": search_restaurants_handler,
    },
    "add_favorite_by_rank": {
        "description": "把当前会话搜索结果中的第 N 家餐厅加入收藏。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
                "session_id": {"type": "string"},
                "rank": {"type": "integer"},
                "collection_id": {"type": "integer"},
            },
            "required": ["user_id", "session_id", "rank"],
        },
        "handler": add_favorite_by_rank_handler,
    },
    "show_favorites": {
        "description": "查看用户当前收藏的餐厅。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
            },
            "required": ["user_id"],
        },
        "handler": show_favorites_handler,
    },
    "get_user_memory": {
        "description": "查看用户长期饮食偏好 Memory。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
            },
            "required": ["user_id"],
        },
        "handler": get_user_memory_handler,
    },
    "refresh_user_memory": {
        "description": "根据收藏夹刷新用户长期 Memory。",
        "parameters": {
            "type": "object",
            "properties": {
                "user_id": {"type": "string"},
            },
            "required": ["user_id"],
        },
        "handler": refresh_user_memory_handler,
    },
}


def openai_tool_definitions() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": item["description"],
                "parameters": item["parameters"],
            },
        }
        for name, item in TOOLS.items()
    ]


async def execute_tool(
    tool_name: str,
    db: AsyncSession,
    short_term_memory: ShortTermMemory,
    arguments: dict[str, Any],
) -> dict[str, Any]:
    tool = TOOLS.get(tool_name)
    if tool is None:
        raise ValueError(f"未知工具：{tool_name}")

    handler: ToolHandler = tool["handler"]
    return await handler(db, short_term_memory, arguments)
