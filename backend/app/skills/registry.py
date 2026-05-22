from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.memory.short_term import ShortTermMemory
from app.skills.base import Skill

class SkillRegistry:
    def __init__(self,skills:list[Skill] | None=None)-> None:
        self._skills:dict[str,Skill]={}

        #在初始化中就已经完成工具的注册，如果传入了工具列表，就把它们注册到技能库中
        for skill in skills or []:
            self.register(skill)

    def prepare_arguments(
    self,
    tool_name: str,
    arguments: dict[str, Any],
    state: dict[str, Any],
    ) -> dict[str, Any]:
        skill = self.get(tool_name)
        if skill is None:
            return dict(arguments or {})
        return skill.prepare_arguments(arguments, state)


    def build_data(
        self,
        tool_name: str,
        result: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        skill = self.get(tool_name)
        if skill is None:
            return result
        return skill.build_data(result)


    def build_template_reply(
        self,
        tool_name: str | None,
        result: dict[str, Any] | None,
        error: str | None,
    ) -> str | None:
        if tool_name is None:
            return None

        skill = self.get(tool_name)
        if skill is None:
            return None

        return skill.build_template_reply(result, error)

    def extract_slots(
        self,
        tool_name: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        skill = self.get(tool_name)
        if skill is None:
            return {"search_slots": state.get("search_slots")}
        return skill.extract_slots(state)

    def check_slots(
        self,
        tool_name: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        skill = self.get(tool_name)
        if skill is None:
            return {"missing_slots": state.get("missing_slots", [])}
        return skill.check_slots(state)

    async def ask_followup(
        self,
        tool_name: str,
        state: dict[str, Any],
        short_term_memory: ShortTermMemory,
    ) -> dict[str, Any]:
        skill = self.get(tool_name)
        if skill is None:
            return {
                "reply": None,
                "data": None,
            }
        return await skill.ask_followup(state, short_term_memory)



    #注册工具
    def register(self,skill:Skill)-> None:
        if skill.name in self._skills:
            raise ValueError(f"duplicate skill {skill.name}")
        self._skills[skill.name]=skill
    
    #获取工具,返回工具的Skill对象，如果工具不存在则返回None
    def get(self,name:str)->Skill | None:
        return self._skills.get(name)
    
    #开放工具定义
    def openai_tool_definitions(self)->list[dict[str,Any]]:
        return [skill.to_openai_tool() for skill in self._skills.values()]
    
    #执行工具,保持和tool_registry对外暴露的执行工具名称和参数相同
    async def execute_tool(
            self,
            tool_name:str,
            db:AsyncSession,
            short_term_memory:ShortTermMemory,
            arguments:dict[str,Any],
    )->dict[str,Any]:
        skill=self.get(tool_name)
        if skill is None:
            raise ValueError(f"未知工具：{tool_name}")
        
        #这里的run相当于执行之前tool_registry里handler的功能，调用相应的skill
        return await skill.run(db,short_term_memory,arguments)
