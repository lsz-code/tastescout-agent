from typing import Any

from app.agent.llm_slot_planner import LLMSlotPlanner
from app.memory.short_term import ShortTermMemory
from app.workflows.agent_state import AgentState


class SearchSlotPlanner:
    """负责搜索槽位抽取、槽位检查和多轮追问。"""

    def __init__(
        self,
        tool_registry: Any,
        llm_slot_planner: LLMSlotPlanner,
        short_term_memory: ShortTermMemory,
    ) -> None:
        """保存 Skill Registry、LLM 槽位规划器和短期记忆访问器。"""
        self.tool_registry = tool_registry
        self.llm_slot_planner = llm_slot_planner
        self.short_term_memory = short_term_memory

    async def extract(self, state: AgentState) -> dict[str, Any]:
        """抽取搜索槽位：规则先行，LLM 只补充规则没覆盖的信息。"""
        if state.get("intent") != "search_restaurants":
            return {"search_slots": state.get("search_slots")}

        #进行规则化槽位抽取
        rule_result = self.tool_registry.extract_slots("search_restaurants", state)
        rule_slots = rule_result.get("search_slots") or {}

        #message：用户这一轮原始输入
        # rule_slots：规则提取器已经抽到的槽位
        # request_location：前端传来的当前位置经纬度
        # short_term_memory：上一轮 pending slots、last_search_context、current_location
        # long_term_memory：用户长期偏好
        llm_slot_plan = await self.llm_slot_planner.plan_search_slots(
            message=state.get("message") or "",
            rule_slots=rule_slots,
            request_location=state.get("location"),
            short_term_memory=state.get("short_term_memory", {}),
            long_term_memory=state.get("long_term_memory", {}),
        )

        if not llm_slot_plan:
            return {"search_slots": rule_slots, "llm_slot_plan": None}

        #llm提取的槽位信息负责对规则抽取的结果进行补全，
        #但不覆盖规则抽取的结果，规则抽取优先级更高
        llm_slots = llm_slot_plan.get("slots") or {}

        #合并规则抽取的槽位和LLM补全的槽位，规则抽取的优先级更高
        merged_slots = {**rule_slots, **llm_slots}

        return {
            "search_slots": merged_slots,
            "llm_slot_plan": llm_slot_plan,
        }

    async def check(self, state: AgentState) -> dict[str, Any]:
        """检查搜索必需槽位是否完整，并决定是否进入追问。"""
        if state.get("intent") != "search_restaurants":
            return {"missing_slots": state.get("missing_slots", [])}
        
        #规则化检查结果
        rule_result = self.tool_registry.check_slots("search_restaurants", state)
        rule_missing_slots = rule_result.get("missing_slots", [])

        #检查LLM规划的槽位补全结果，看看是否还有缺失的槽位需要追问的
        llm_slot_plan = state.get("llm_slot_plan")
        if not isinstance(llm_slot_plan, dict):
            return {"missing_slots": rule_missing_slots}

        #LLM规划的结果里缺失槽位列表必须是个列表，且只能包含location和cuisine这两个可能的槽位，
        #否则就退回只用规则检查的结果
        llm_missing_slots = llm_slot_plan.get("missing_slots")
        if not isinstance(llm_missing_slots, list):
            return {"missing_slots": rule_missing_slots}

        #如果LLM规划的结果里说不需要追问了，那就直接返回空缺失槽位，进入搜索流程
        if not bool(llm_slot_plan.get("should_ask_followup")):
            return {"missing_slots": []}

        #如果LLM规划的结果里说需要追问，那就用LLM规划的缺失槽位，进入追问流程
        normalized_missing_slots = [
            item for item in llm_missing_slots if item in {"location", "cuisine"}
        ]
        return {"missing_slots": normalized_missing_slots or rule_missing_slots}

    async def ask_followup(self, state: AgentState) -> dict[str, Any]:
        """生成追问文本，并把未完成的搜索槽位写入短期记忆。"""
        llm_slot_plan = state.get("llm_slot_plan")
        if isinstance(llm_slot_plan, dict):
            followup_question = llm_slot_plan.get("followup_question")
            if isinstance(followup_question, str) and followup_question.strip():
                slots = state.get("search_slots") or {}
                missing_slots = state.get("missing_slots") or []
                session_id = state.get("session_id")

                if session_id:
                    await self.short_term_memory.update(
                        session_id,
                        {
                            "pending_search_slots": slots,
                            "missing_slots": missing_slots,
                            "last_intent": "ask_followup",
                        },
                    )

                return {
                    "reply": followup_question.strip(),
                    "data": {
                        "needs_followup": True,
                        "missing_slots": missing_slots,
                        "partial_slots": slots,
                    },
                }

        return await self.tool_registry.ask_followup(
            "search_restaurants",
            state,
            self.short_term_memory,
        )
