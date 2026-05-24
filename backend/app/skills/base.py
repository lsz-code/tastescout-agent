#这里把之前通过意图识别选择的工具统一改成的SKILL，定义它们的统一接口
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.short_term import ShortTermMemory


class Skill:
    name: str
    description: str
    parameters: dict[str, Any]

    #新增三个基类方法
    def prepare_arguments(
            self,
            arguments: dict[str, Any],
            state: dict[str, Any],
    ):
        normalized = dict(arguments or {})

        user_id = state.get("user_id")
        if user_id is not None:
            normalized["user_id"] = user_id
        
        return normalized
    
    def build_data(
            self,
            result: dict[str, Any] | None,
    ):
        return result
    
    def build_template_reply(
            self,
            result: dict[str, Any] | None,
            error:str | None,
    )-> str | None:
        if error:
            return f"操作失败：{error}"
        return None

    def extract_slots(self, state: dict[str, Any]) -> dict[str, Any]:
        return {"search_slots": state.get("search_slots")}

    def check_slots(self, state: dict[str, Any]) -> dict[str, Any]:
        return {"missing_slots": state.get("missing_slots", [])}

    async def ask_followup(
            self,
            state: dict[str, Any],
            short_term_memory: ShortTermMemory,
    ) -> dict[str, Any]:
        return {
            "reply": None,
            "data": None,
        }
        

    def to_openai_tool(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }

    async def run(
        self,
        db: AsyncSession,
        short_term_memory: ShortTermMemory,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        raise NotImplementedError
