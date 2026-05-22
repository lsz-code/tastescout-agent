from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.short_term import ShortTermMemory
from app.schemas.favorite import AddFavoriteRestaurantRequest
from app.services.favorite_service import FavoriteService
from app.skills.base import Skill


class AddFavoriteByRankSkill(Skill):
    name = "add_favorite_by_rank"
    description = "把当前会话搜索结果中的第 N 家餐厅加入收藏。"
    parameters: dict[str, Any] = {
        "type": "object",
        "properties": {
            "user_id": {"type": "string"},
            "session_id": {"type": "string"},
            "rank": {"type": "integer"},
            "collection_id": {"type": "integer"},
        },
        "required": ["user_id", "session_id", "rank"],
    }

    # 执行技能逻辑
    async def run(
        self,
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
    
    #准备参数
    def prepare_arguments(
        self,
        arguments: dict[str, Any],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        normalized = super().prepare_arguments(arguments, state)

        session_id = state.get("session_id")
        if session_id is not None:
            normalized["session_id"] = session_id

        normalized.setdefault("rank", 1)
        return normalized
    
    #构建参数响应
    def build_data(
        self,
        result: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if result is None:
            return None

        return {
            "favorite": result,
            "restaurant": result.get("restaurant"),
        }

    #构建模版回答
    def build_template_reply(
        self,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> str | None:
        if error:
            return f"操作失败：{error}"

        result = result or {}
        restaurant = result.get("restaurant") or {}
        rank = result.get("rank")
        name = restaurant.get("name") or "这家餐厅"
        return f"已帮你收藏第 {rank} 家：{name}。"

class ShowFavoritesSkill(Skill):
    name = "show_favorites"
    description = "查看用户当前收藏的餐厅。"
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
        service = FavoriteService(db)
        favorites = await service.list_favorites(arguments["user_id"])
        return {
            "favorites": [item.model_dump(mode="json") for item in favorites],
        }
    

    def build_data(
        self,
        result: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        if result is None:
            return None
        return {"favorites": result.get("favorites") or []}


    def build_template_reply(
        self,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> str | None:
        if error:
            return f"操作失败：{error}"
        return "这是你当前收藏的餐厅。"

    @staticmethod
    def _is_reroll_intent(message: str) -> bool:
        return any(
            keyword in message
            for keyword in [
                "再推荐几家",
                "换几家",
                "还有别的吗",
                "还有别的么",
                "还有其他的吗",
                "有没有其他的",
                "不想吃这些",
                "再来几个",
                "再推荐一些别的",
                "重新推荐",
                "换一批",
            ]
        )