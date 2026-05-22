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
                    "你是 TasteScout，一个中文美食生活助手。"
                    "你擅长帮用户找附近美食、餐厅、酒馆、奶茶、夜宵，也可以轻松自然地闲聊。"
                    "你的风格像懂吃、会聊天的朋友，不像机械客服。"
                    "你现在只负责选择后端提供的业务级工具，不能调用或臆造高德 MCP 工具。"
                    "不要把所有消息都当成搜索任务；用户开玩笑、吐槽、闲聊，或者只是表达情绪时，不要选择任何工具。"
                    "如果用户明显想找吃的、找店、查餐厅，调用 search_restaurants。"
                    "位置是搜索的关键；菜系、预算、场景都不是必填项。"
                    "如果用户之前提供过位置，优先复用上下文，不要因为本轮没说位置就放弃搜索。"
                    "用户说“再推荐一些”“换一批”“还有别的吗”时，默认复用上一次搜索条件。"
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

    #信息提取agent，从用户输入和记忆中提取结构化信息，帮助工具选择和回复生成。
    async def extract_message_context(
            self,
            message: str,
            short_term_memory: dict[str, Any],
            long_term_memory: dict[str, Any],
    ) -> dict[str, Any] | None:
        if not self.available:
            return None

        payload = {
            "model": self.models,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 TasteScout 的中文信息解析器，只负责把用户输入解析成结构化 JSON。"
                        "不要输出自然语言，不要解释，不要使用 Markdown。"
                        "只能返回一个 JSON object。"
                        "可选 intent 只有：search_restaurants、casual_chat、unknown。"
                        "用户明显想找吃的、找餐厅、找店、找酒馆、找奶茶、找夜宵时，intent=search_restaurants。"
                        "用户只是开玩笑、吐槽、闲聊、表达情绪且没有明确搜索需求时，intent=casual_chat。"
                        "用户说“再推荐一些”“换一批”“还有别的吗”“不想吃这些”时，intent=search_restaurants，is_continue_recommendation=true。"
                        "只从用户原文和已给记忆中提取信息，不要编造具体餐厅、地址、经纬度。"
                        "如果用户说“我现在在海南海口市”“人在海口”“海口这边”，address 可填对应地点。"
                        "如果用户找具体店名，把店名放入 keyword，filters.cuisine 保持为空。"
                        "如果用户想找吃的但没有具体菜系或店名，keyword 使用“美食”。"
                        "菜系、预算、场景都不是必填项。"
                        "返回字段：intent, address, city, location, keyword, cuisine, budget, scene, radius, limit, is_continue_recommendation。"
                        "未知或没有的信息用 null，不要省略 intent。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "message": message,
                            "short_term_memory": short_term_memory,
                            "long_term_memory": long_term_memory,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "enable_thinking": False,
            "temperature": 0.0,
        }
        data = await self._chat_completions(payload)
        choice = (data.get("choices") or [{}])[0]
        assistant_message = choice.get("message") or {}
        content = assistant_message.get("content")
        if not isinstance(content, str) or not content.strip():
            return None

        return self._loads_json_object(content)
    
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
                        "你是 TasteScout，一个中文美食生活助手。"
                        "你擅长帮用户找附近美食、餐厅、酒馆、奶茶、夜宵，也可以轻松自然地闲聊。"
                        "你的风格像一个懂吃、会聊天的朋友，而不是机械客服。"
                        "根据后端业务工具结果，用自然、简洁、口语化的中文回复用户。"
                        "不要频繁说“请提供位置和菜系”，菜系、预算、场景都不是必填项。"
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

    #闲聊回复生成Agent，专门处理用户的闲聊、吐槽、情绪表达等非搜索意图，保持自然友好的对话氛围。
    async def generate_casual_reply(
            self,
            message: str,
            short_term_memory: dict[str, Any],
            long_term_memory: dict[str, Any],
    ) -> str | None:
        if not self.available:
            return None

        payload = {
            "model": self.models,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是 TasteScout，一个懂美食、会聊天的中文生活助手。"
                        "你可以轻松幽默地回应用户，但不要油腻，不要过度夸张。"
                        "如果用户只是闲聊，就自然回应。"
                        "如果用户表达饿、纠结、懒得选，可以轻轻引导："
                        "“要不我帮你看看附近有什么好吃的？”"
                        "不要强行调用工具。"
                        "不要编造具体餐厅。"
                        "回复要自然、友好、口语化，尽量简洁。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "message": message,
                            "short_term_memory": short_term_memory,
                            "long_term_memory": long_term_memory,
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "enable_thinking": False,
            "temperature": 0.7,
        }
        data = await self._chat_completions(payload)
        choice = (data.get("choices") or [{}])[0]
        assistant_message = choice.get("message") or {}
        content = assistant_message.get("content")
        return content.strip() if isinstance(content, str) and content.strip() else None

    #加载json格式数据
    @staticmethod
    def _loads_json_object(content: str) -> dict[str, Any] | None:
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()

        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None

        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            return None

        return parsed if isinstance(parsed, dict) else None
    
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
        
        
