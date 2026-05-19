import json
from typing import Any

import httpx

from app.core.config import settings

#AgentLLMClient负责与后端LLM服务交互，提供工具选择和回复生成的功能。
#它通过HTTP请求调用LLM API，根据用户输入和当前记忆状态来选择合适的工具，并生成自然语言回复。
class AgentLLMClient:
    def __init__(self)->None:
        self.base_url = settings.LLM_BASE_URL
        self.api_key = settings.LLM_API_KEY
        self.models = settings.LLM_MODEL
        self.timeout = settings.LLM_TIMEOUT_SECONDS

    @property
    def available(self) -> bool:
        return bool(self.base_url and self.api_key)

    #工具选择agent
    async def select_tool(
            self,
            message:str,
            user_id:str,
            session_id:str,
            short_term_memory:dict[str, Any],
            long_term_memory:dict[str, Any],
            tools:list[dict[str, Any]],
    )->dict[str,Any]|None:
        if not self.available:
            return None
        
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 TasteScout Agent 的工具选择器。"
                    "你只能选择后端提供的业务级工具，不能调用或臆造高德 MCP 工具。"
                    "如果用户想找餐厅，调用 search_restaurants。"
                    "如果用户想收藏第 N 家，调用 add_favorite_by_rank。"
                    "如果用户想看收藏，调用 show_favorites。"
                    "如果用户想看偏好或记忆，调用 get_user_memory。"
                    "如果用户想刷新长期记忆，调用 refresh_user_memory。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "user_id": user_id,
                        "session_id": session_id,
                        "message": message,
                        "short_term_memory": short_term_memory,
                        "long_term_memory": long_term_memory,
                    },
                    ensure_ascii=False,
                ),
            },
        ]

        payload = {
            "model": self.models,
            "messages":messages,
            "tools":tools,
            "tool_choice": "auto",
            "enable_thinking":False,
            "temperature": 0.0,
        }

        data = await self._chat_completions(payload)
        choice = (data.get("choices") or [{}])[0]
        assistant_message = choice.get("message") or {}
        tool_calls = assistant_message.get("tool_calls") or []
        if not tool_calls:
            return None
        
        function = tool_calls[0].get("function") or {}
        name = function.get("name")
        raw_arguments = function.get("arguments") or {}

        try:
            arguments = json.loads(raw_arguments)
        except json.JSONDecodeError:
            arguments = {}

        if not name:
            return None
        
        return {
            "tool_name":name,
            "arguments":arguments,
        }
    
    #回复生成Agent
    async def generate_reply(
            self,
            user_message:str,
            tool_name:str|None,
            tool_result:dict[str, Any]|None,
    )-> str | None:
        if not self.available:
            return None
        
        payload = {
            "model":self.models,
            "messages":[
                                {
                    "role": "system",
                    "content": (
                        "你是 TasteScout Agent。根据后端业务工具结果，用简洁自然的中文回复用户。"
                        "不要提及内部 MCP、高德工具、函数调用或技术实现。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "message": user_message,
                            "tool_name": tool_name,
                            "tool_result": tool_result,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "enable_thinking": False,
            "temperature": 0.4,
        }
        data = await self._chat_completions(payload)
        choice = (data.get("choices") or [{}])[0]
        assistant_message = choice.get("message") or {}
        content = assistant_message.get("content")
        return content.strip() if isinstance(content,str) and content.strip() else None
    
    #通用的Chat Completions接口调用方法
    async def _chat_completions(self,payload:dict[str, Any])->dict[str, Any]:
        url = self.base_url.rstrip("/")+"/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, headers=headers, json=payload)
            if response.status_code >=400:
                # Log the error details for debugging
                    print("LLM status:", response.status_code)
                    print("LLM response:", response.text)
            response.raise_for_status()
            return response.json()
        
        