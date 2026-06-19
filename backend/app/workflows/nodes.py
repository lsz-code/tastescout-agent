from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent import tool_registry as default_tool_registry
from app.agent.intent_parser import IntentParser
from app.agent.llm_client import AgentLLMClient
from app.agent.llm_slot_planner import LLMSlotPlanner
from app.memory.short_term import ShortTermMemory
from app.services.memory_service import MemoryService
from app.workflows.agent_state import AgentState
from app.workflows.intent_planner import IntentPlanner
from app.workflows.memory_loader import MemoryLoader
from app.workflows.response_planner import ResponsePlanner
from app.workflows.search_slot_planner import SearchSlotPlanner
from app.workflows.state_utils import missing_required_field


class AgentWorkflowNodes:
    """LangGraph 节点适配层。

    这个类只保留 Workflow 对外暴露的节点方法。具体的记忆加载、意图规划、
    槽位规划和回复生成分别拆到独立类中，避免所有通用逻辑堆在一个文件里。
    """

    def __init__(
        self,
        db: AsyncSession,
        short_term_memory: ShortTermMemory,
        agent_llm_client: AgentLLMClient | None = None,
        intent_parser: IntentParser | None = None,
        tool_registry: Any = None,
    ) -> None:
        """初始化 Workflow 节点依赖和四个通用规划器。"""
        self.db = db
        self.short_term_memory = short_term_memory
        self.agent_llm_client = agent_llm_client or AgentLLMClient()
        self.intent_parser = intent_parser or IntentParser()
        self.tool_registry = tool_registry or default_tool_registry

        memory_service = MemoryService(db)
        llm_slot_planner = LLMSlotPlanner(self.agent_llm_client)

        self.memory_loader = MemoryLoader(
            short_term_memory=self.short_term_memory,
            memory_service=memory_service,
        )
        self.intent_planner = IntentPlanner(
            agent_llm_client=self.agent_llm_client,
            intent_parser=self.intent_parser,
            tool_registry=self.tool_registry,
        )
        self.search_slot_planner = SearchSlotPlanner(
            tool_registry=self.tool_registry,
            llm_slot_planner=llm_slot_planner,
            short_term_memory=self.short_term_memory,
        )
        self.response_planner = ResponsePlanner(
            agent_llm_client=self.agent_llm_client,
            tool_registry=self.tool_registry,
        )

    async def load_memory(self, state: AgentState) -> dict[str, Any]:
        """加载短期记忆和长期记忆。"""
        return await self.memory_loader.load(state)

    async def classify_intent(self, state: AgentState) -> dict[str, Any]:
        """判断用户意图，并准备可能需要的工具参数。"""
        return await self.intent_planner.plan(state)

    async def extract_slots(self, state: AgentState) -> dict[str, Any]:
        """在搜索意图下抽取餐厅搜索槽位。"""
        return await self.search_slot_planner.extract(state)

    async def check_slots(self, state: AgentState) -> dict[str, Any]:
        """检查搜索槽位是否完整，决定是否追问。"""
        return await self.search_slot_planner.check(state)

    async def ask_followup(self, state: AgentState) -> dict[str, Any]:
        """生成多轮追问，并保存待补全槽位。"""
        return await self.search_slot_planner.ask_followup(state)

    async def search_restaurants(self, state: AgentState) -> dict[str, Any]:
        """执行餐厅搜索 Skill。"""
        return await self._run_tool(state, "search_restaurants")

    async def add_favorite(self, state: AgentState) -> dict[str, Any]:
        """执行按排名收藏餐厅 Skill。"""
        return await self._run_tool(state, "add_favorite_by_rank")

    async def show_favorites(self, state: AgentState) -> dict[str, Any]:
        """执行查看收藏 Skill。"""
        return await self._run_tool(state, "show_favorites")

    async def get_memory(self, state: AgentState) -> dict[str, Any]:
        """执行查看长期记忆 Skill。"""
        return await self._run_tool(state, "get_user_memory")

    async def refresh_memory(self, state: AgentState) -> dict[str, Any]:
        """执行刷新长期记忆 Skill。"""
        return await self._run_tool(state, "refresh_user_memory")

    async def casual_chat(self, state: AgentState) -> dict[str, Any]:
        """执行非工具型闲聊回复。"""
        return await self.response_planner.casual_chat(state)

    async def fallback(self, state: AgentState) -> dict[str, Any]:
        """兜底节点，保证无法识别意图时也能进入回复生成。"""
        return {
            "intent": "fallback",
            "tool_result": None,
            "data": None,
        }

    async def generate_response(self, state: AgentState) -> dict[str, Any]:
        """生成最终回复。"""
        return await self.response_planner.generate(state)

    async def _run_tool(
        self,
        state: AgentState,
        tool_name: str,
    ) -> dict[str, Any]:
        """统一执行业务 Skill，并把结果写回 LangGraph state。"""
        missing_error = missing_required_field(state)
        if missing_error:
            return {
                "intent": "fallback",
                "tool_result": None,
                "data": None,
                "error": missing_error,
            }

        #这里的tool_name是作为选择的Skill的标识符，和tool_registry里注册的工具名称保持一致
        arguments = self.tool_registry.prepare_arguments(
            tool_name=tool_name,
            arguments=state.get("planned_tool_args", {}),
            state=state,
        )
        tool_call = {
            "tool_name": tool_name,
            "arguments": arguments,
            "result": None,
            "success": True,
            "error": None,
        }

        #处理前置条件不足的情况，直接返回特殊的结果
        #build_data的作用是把工具执行结果转换成回复生成阶段需要的格式，
        # 这样就算是前置条件不足没有真正调用工具，也能让回复生成阶段拿到一个统一
        # 格式的数据来生成回复，而不需要关心前置条件不足的特殊情况
        special_result = self._build_search_special_result(tool_name, arguments)
        if special_result is not None:
            tool_call["result"] = special_result
            return {
                "intent": tool_name,
                "tool_calls": state.get("tool_calls", []) + [tool_call],
                "tool_result": special_result,
                "data": self.tool_registry.build_data(tool_name, special_result),
                "error": None,
            }
        #正常执行工具
        try:
            result = await self.tool_registry.execute_tool(
                tool_name=tool_name,
                db=self.db,
                short_term_memory=self.short_term_memory,
                arguments=arguments,
            )

            #执行完工具后，如果是搜索工具，就清理掉上一轮追问遗留的待补槽位，避免对下一轮搜索造成干扰
            await self._clear_pending_search_slots_if_needed(state, tool_name)

            tool_call["result"] = result
            return {
                "intent": tool_name,
                "tool_calls": state.get("tool_calls", []) + [tool_call],
                "tool_result": result,
                "data": self.tool_registry.build_data(tool_name, result),
                "error": None,
            }
        except Exception as exc:
            tool_call["success"] = False
            tool_call["error"] = str(exc)
            return {
                "intent": tool_name,
                "tool_calls": state.get("tool_calls", []) + [tool_call],
                "tool_result": None,
                "data": None,
                "error": str(exc),
            }

    @staticmethod
    def _build_search_special_result(
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any] | None:
        """处理搜索前置条件不足的特殊返回，不真正调用搜索服务。"""
        if tool_name != "search_restaurants":
            return None

        if arguments.get("missing_location"):
            return {"missing_location": True, "restaurants": []}

        if arguments.get("missing_search_context"):
            return {"missing_search_context": True, "restaurants": []}

        return None

    async def _clear_pending_search_slots_if_needed(
        self,
        state: AgentState,
        tool_name: str,
    ) -> None:
        """搜索成功后清理上一轮追问遗留的待补槽位。"""
        if tool_name != "search_restaurants" or not state.get("session_id"):
            return

        await self.short_term_memory.update(
            state["session_id"],
            {
                "pending_search_slots": None,
                "missing_slots": [],
            },
        )
