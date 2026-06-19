import json
from typing import Any

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import settings


MAX_CURRENT_CANDIDATES = 20
MAX_RECOMMENDED_POI_IDS = 100
MAX_MATCH_REASONS = 5
MAX_RECOMMENDED_DISHES = 5
MAX_TEXT_LENGTH = 500


#构建shortmemeory
class ShortTermMemory:
    def __init__(self,redis_url:str,ttl_seconds:int=1800):
        self.redis_url = redis_url
        self.ttl_seconds = ttl_seconds
        #使用redis的异步客户端
        self.client = redis.from_url(redis_url,decode_responses=True)

    def _key(self, session_id: str) -> str:
        return f"tastescout:session:{session_id}:memory"
    

    #根据session_id获取短期记忆
    async def get(self,session_id:str)->dict[str,Any]:
        try:
            #从redis中获取数据，如果不存在则返回空字典
            value = await self.client.get(self._key(session_id))
            if value is None:
                return {}
            return json.loads(value)
        except (RedisError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"Failed to get short-term memory: {exc}") from exc
    

    #设置短期记忆
    async def set(self,session_id:str,data:dict[str,Any])->dict[str,Any]:
        try:
            data = self._prune_memory(data)
            #设置短期记忆到redis中去
            await self.client.set(
                self._key(session_id),
                json.dumps(data,ensure_ascii=False),
                ex=self.ttl_seconds,
            )
            return data
        except(RedisError, TypeError) as exc:
            raise RuntimeError(f"Failed to set short-term memory: {exc}") from exc
    

    #更新短期记忆到redis
    async def update(
            self,
            session_id:str,
            patch: dict[str,Any],
    ) -> dict[str,Any]:
        memory = await self.get(session_id)
        memory.update(patch)
        return await self.set(session_id,memory)
    

    #删除整个会话对应的redis中的短期记忆
    async def delete(self,session_id:str)->bool:
        try:
            deleted = await self.client.delete(self._key(session_id))
            return deleted > 0
        except RedisError as exc:
            raise RuntimeError(f"Failed to delete short-term memory: {exc}") from exc
    

    #清空候选餐厅
    async def clear_candiates(self,session_id:str)->dict[str,Any]:
        memory = await self.get(session_id)
        memory["current_candidates"] = []
        return await self.set(session_id,memory)
    

    #追加一个候选餐厅
    async def append_candidates(
            self,
            session_id:str,
            restaurants:dict[str,Any],
    )-> dict[str,Any]:
        memory  = await self.get(session_id)
        candidates = memory.get("current_candidates")

        if not isinstance(candidates,list):
            candidates = []
        
        candidates.append(restaurants)
        memory["current_candidates"] = candidates

        return await self.set(session_id,memory)

    @classmethod
    def _prune_memory(cls, data: dict[str, Any]) -> dict[str, Any]:
        memory = dict(data or {})

        candidates = memory.get("current_candidates")
        if isinstance(candidates, list):
            memory["current_candidates"] = [
                cls._normalize_candidate(item)
                for item in candidates[-MAX_CURRENT_CANDIDATES:]
                if isinstance(item, dict)
            ]

        recommended_poi_ids = memory.get("recommended_poi_ids")
        if isinstance(recommended_poi_ids, list):
            memory["recommended_poi_ids"] = cls._limit_unique_strings(
                recommended_poi_ids,
                MAX_RECOMMENDED_POI_IDS,
            )

        last_search_context = memory.get("last_search_context")
        if isinstance(last_search_context, dict):
            memory["last_search_context"] = cls._normalize_search_context(
                last_search_context
            )

        pending_search_slots = memory.get("pending_search_slots")
        if isinstance(pending_search_slots, dict):
            memory["pending_search_slots"] = cls._normalize_search_context(
                pending_search_slots
            )

        for field in (
            "current_address",
            "current_search_keyword",
            "current_search_query",
        ):
            if field in memory:
                memory[field] = cls._limit_text(memory.get(field), MAX_TEXT_LENGTH)

        return memory

    @classmethod
    def _normalize_candidate(cls, item: dict[str, Any]) -> dict[str, Any]:
        candidate: dict[str, Any] = {}
        allowed_fields = (
            "rank",
            "poi_id",
            "name",
            "photo",
            "address",
            "location",
            "cuisine_type",
            "rating",
            "avg_price",
            "distance",
            "score",
            "match_reasons",
            "recommended_dishes",
            "review_summary",
            "recommend_reason",
        )
        for field in allowed_fields:
            value = item.get(field)
            if value is not None:
                candidate[field] = value

        for field in (
            "poi_id",
            "name",
            "photo",
            "address",
            "cuisine_type",
            "review_summary",
            "recommend_reason",
        ):
            if field in candidate:
                candidate[field] = cls._limit_text(candidate.get(field), MAX_TEXT_LENGTH)

        match_reasons = candidate.get("match_reasons")
        if isinstance(match_reasons, list):
            candidate["match_reasons"] = [
                cls._limit_text(reason, 120)
                for reason in match_reasons[:MAX_MATCH_REASONS]
                if reason
            ]

        dishes = candidate.get("recommended_dishes")
        if isinstance(dishes, list):
            candidate["recommended_dishes"] = dishes[:MAX_RECOMMENDED_DISHES]

        return candidate

    @classmethod
    def _normalize_search_context(cls, context: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = {}
        for field in (
            "address",
            "location",
            "keyword",
            "search_query",
            "search_type",
            "city",
            "cuisine",
            "budget",
            "scene",
            "radius",
            "limit",
        ):
            value = context.get(field)
            if value is not None and value != "":
                normalized[field] = value

        for field in (
            "address",
            "keyword",
            "search_query",
            "search_type",
            "city",
            "cuisine",
            "scene",
        ):
            if field in normalized:
                normalized[field] = cls._limit_text(normalized.get(field), MAX_TEXT_LENGTH)

        filters = context.get("filters")
        if isinstance(filters, dict):
            normalized_filters = {
                key: filters[key]
                for key in ("cuisine", "max_price", "min_rating", "scene")
                if key in filters and filters[key] is not None and filters[key] != ""
            }
            if normalized_filters:
                normalized["filters"] = normalized_filters

        return normalized

    @staticmethod
    def _limit_unique_strings(values: list[Any], limit: int) -> list[str]:
        seen: set[str] = set()
        result_reversed: list[str] = []
        for item in reversed(values):
            text = str(item).strip() if item is not None else ""
            if not text or text in seen:
                continue
            seen.add(text)
            result_reversed.append(text)
            if len(result_reversed) >= limit:
                break
        return list(reversed(result_reversed))

    @staticmethod
    def _limit_text(value: Any, limit: int) -> str | None:
        if value is None:
            return None
        text = str(value)
        return text[:limit]
    
_short_term_memory = ShortTermMemory(settings.REDIS_URL)

def get_short_term_memory() -> ShortTermMemory:
    return _short_term_memory

