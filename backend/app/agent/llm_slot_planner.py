import json
from typing import Any

from app.agent.llm_client import AgentLLMClient


class LLMSlotPlanner:
    """
    使用LLM做搜索槽位补全和追问规划

    注意：
    这里不是让LLM输出完整思维链。
    LLM只允许输出结构化JSON，供Workflow使用
    """

    def __init__(self,llm_client: AgentLLMClient | None = None)-> None:
        """
        初始化LLM槽位规划器
        Args:
            llm_client :可选LLM客户端。默认使用AgentLLMClient。
        """
        self.llm_client = llm_client or AgentLLMClient()

    async def plan_search_slots(
            self,
            message:str,
            rule_slots: dict[str,Any],
            short_term_memory: dict[str,Any],
            long_term_memory: dict[str,Any],
            request_location: dict[str,Any] | None = None,    
    )->dict[str,Any] | None:
        """
        根据用户信息,规则槽位和记忆上下文,生成结构化槽位规划
        也就是让LLM创建一个JSON对象,描述需要补全的槽位和追问规划

        返回结构示例:
        {
          "intent": "search_restaurants",
          "slots": {
            "address": "望京SOHO",
            "location": {"longitude": 116.4, "latitude": 39.9},
            "keyword": "川菜",
            "cuisine": "川菜",
            "budget": 200,
            "scene": "朋友聚餐",
            "radius": 3000,
            "limit": 5
          },
          "missing_slots": [],
          "should_ask_followup": false,
          "followup_question": null,
          "assumptions": ["用户说随便推荐，因此使用美食作为关键词"]
        }

        如果 LLM 不可用、调用失败、JSON 不合法，则返回 None。
        """
        if not self.llm_client.available:
            return None
        
        payload = {
            "model":self.llm_client.models,
            "messages":[
                {
                    "role":"system",
                    "content": (
                        "你是 TasteScout 的餐厅搜索槽位规划器。"
                        "你需要根据用户消息、规则提取槽位、短期记忆和长期记忆，"
                        "判断餐厅搜索需要哪些参数。"
                        "不要输出思维链，不要输出推理过程，只输出严格 JSON。"
                        "JSON 字段必须包括："
                        "intent, slots, missing_slots, should_ask_followup, followup_question, assumptions。"
                        "intent 只能是 search_restaurants 或 unknown。"
                        "slots 可包含 address, location, keyword, cuisine, budget, scene, radius, limit。"
                        "missing_slots 只能包含 location, cuisine。"
                        "如果用户说随便推荐，且已有 location 或 address，可以把 keyword 设置为 美食，不必追问 cuisine。"
                        "如果用户说附近/周边，但没有 location/address，需要追问 location。"
                        "followup_question 必须是中文。"
                    ),
                },
                {
                    "role":"user",
                    "content":json.dumps(
                        {
                            "message":message,
                            "rule_slots":rule_slots,
                            "request_location":request_location,
                            "short_term_memory":{
                                "pending_search_slots":short_term_memory.get(
                                    "pending_search_slots"
                                ),
                                "last_search_context":short_term_memory.get(
                                    "last_search_context"
                                ),
                                "current_location":short_term_memory.get(
                                    "current_location"
                                ),
                            },
                            "long_term_memory":long_term_memory,
                        },
                        ensure_ascii=False
                    ),
                },
            ],
            "temperature": 0.1,
            "enable_thinking": False,
        }

        #进行模型调用
        try:
            data=await self.llm_client._chat_completions(payload)
            content=(
                (data.get("choices")or [{}])[0]
                .get("message",{})
                .get("content")
            )
            parsed = self._parse_json_content(content)
            if not parsed:
                return None

            return self._normalize_plan(parsed)
        except Exception:
            return None
        
    def _normalize_plan(self,plan:dict[str,Any])->dict[str,Any]:
        """
        清洗LLM返回的槽位规划结果.

        目的:
        - 防止 LLM 输出额外字段污染 Workflow。
        - 保证 missing_slots、slots、assumptions 的类型稳定。
        - 过滤非法 intent。
        """
        intent = plan.get("intent")
        if intent not in ["search_restaurants","unknown"]:
            intent = "unknown"

        slots = plan.get("slots")
        if not isinstance(slots,dict):
            slots = {}
        
        normalized_slots:dict[str,Any]={}
        for field in (
            "address",
            "location",
            "keyword",
            "cuisine",
            "budget",
            "scene",
            "radius",
            "limit",
        ):
            value = slots.get(field)
            if value is not None and value != "":
                normalized_slots[field] = value
        
        location = normalized_slots.get("location")
        if isinstance(location,dict):
            longitude = self._to_float(location.get("longitude"))
            latitude = self._to_float(location.get("latitude"))
            if longitude is not None and latitude  is not None:
                normalized_slots["location"]={
                    "longitude":longitude,
                    "latitude":latitude,
                }
            else:
                normalized_slots.pop("location",None)
        
        for field in ("budget","radius","limit"):
            if field in normalized_slots:
                value = self._to_int(normalized_slots[field])
                if value is None:
                    normalized_slots.pop(field,None)
                else:
                    normalized_slots[field]=value

        missing_slots = plan.get("missing_slots")
        if not isinstance(missing_slots,list):
            missing_slots = []
        
        missing_slots = [
            item for item in missing_slots if item in ["location","cuisine"]
        ]

        followup_question = plan.get("followup_question")
        if not isinstance(followup_question,str) or not followup_question.strip():
            followup_question = None
        else:
            followup_question = followup_question.strip()

        assumptions = plan.get("assumptions")
        if not isinstance(assumptions,list):
            assumptions = []
        assumptions = [
            item.strip()
            for item in assumptions
            if isinstance(item,str) and item.strip()
        ]

        return {
            "intent": intent,
            "slots": normalized_slots,
            "missing_slots": missing_slots,
            "should_ask_followup": bool(plan.get("should_ask_followup")),
            "followup_question": followup_question,
            "assumptions": assumptions,
        }
    
    @staticmethod
    def _parse_json_content(content:Any)->dict[str,Any] | None:
        """
        解析LLM返回的JSON内容.

        兼容:
        1.直接JSON字符串.
        2.```json ... ```代码块。
        """

        if not isinstance(content,str):
            return None
        
        text = content.strip()
        if text.startswith("```"):
            text = text.strip("`").strip()
            if text.startswith("json"):
                text = text[4:].strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            return None
    
        return parsed if isinstance(parsed,dict) else None

    
    @staticmethod
    def _to_int(value:Any)->int | None:
        """
        把输入转换成int,失败返回None.
        """
        if value is None or value == "":
            return None

        try:
            return int(float(value))
        except(TypeError,ValueError):
            return None
        
    @staticmethod
    def _to_float(value:Any)->float | None:
        """
        把输入转换成float,失败返回None.
        """
        if value is None or value == "":
            return None

        try:
            return float(value)
        except(TypeError,ValueError):
            return None