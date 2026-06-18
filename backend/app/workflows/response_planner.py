from typing import Any

from app.agent.llm_client import AgentLLMClient
from app.workflows.agent_state import AgentState


class ResponsePlanner:
    """负责把工具结果或闲聊意图转换成用户可读的中文回复。"""

    def __init__(
        self,
        agent_llm_client: AgentLLMClient,
        tool_registry: Any,
    ) -> None:
        """保存 LLM 客户端和 Skill Registry 回复模板代理。"""
        self.agent_llm_client = agent_llm_client
        self.tool_registry = tool_registry

    async def casual_chat(self, state: AgentState) -> dict[str, Any]:
        """处理无需工具调用的普通闲聊回复。"""
        reply: str | None = None
        try:
            reply = await self.agent_llm_client.generate_casual_reply(
                message=state.get("message") or "",
                short_term_memory=state.get("short_term_memory", {}),
                long_term_memory=state.get("long_term_memory", {}),
            )
        except Exception:
            reply = None

        if reply is None:
            reply = (
                "听起来你已经进入“不知道吃什么但必须吃点什么”的状态了。"
                "要不要我顺手帮你看看附近有什么靠谱的？"
            )

        return {
            "intent": "casual_chat",
            "reply": reply,
            "tool_result": None,
            "tool_calls": [],
            "data": {"casual_chat": True},
            "memory_used": True,
        }

    async def generate(self, state: AgentState) -> dict[str, Any]:
        """优先使用已有回复，其次 LLM 生成，最后回退到 Skill 模板。"""
        if state.get("reply"):
            return {"reply": state["reply"]}

        reply: str | None = None
        message = state.get("message")

        if not state.get("error") and message is not None:
            try:
                reply = await self.agent_llm_client.generate_reply(
                    user_message=message,
                    tool_name=state.get("intent"),
                    tool_result=state.get("tool_result"),
                )
            except Exception:
                reply = None

        if reply is None:
            reply = self.tool_registry.build_template_reply(
                tool_name=state.get("intent"),
                result=state.get("tool_result"),
                error=state.get("error"),
            )

        if reply is None:
            reply = "我可以帮你搜索餐厅、收藏推荐结果、查看收藏夹或查看口味偏好。"

        return {"reply": reply}
