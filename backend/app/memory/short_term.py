import json
from typing import Any

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.config import settings

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
            #设置短期记忆到redis中去
            await self.client.set(
                self._key(session_id),
                json.dumps(data,ensure_ascii=False),
                ex=self.ttl_seconds,
            )
            print("redis key =", self._key(session_id))
            print("redis exists =", await self.client.exists(self._key(session_id)))
            print("redis value =", await self.client.get(self._key(session_id)))
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
    
_short_term_memory = ShortTermMemory(settings.REDIS_URL)

def get_short_term_memory() -> ShortTermMemory:
    return _short_term_memory

