1. 项目骨架 ✅
2. Docker Compose ✅
3. 数据库模型 ✅
4. 用户 bootstrap ← 当前阶段

5. 收藏夹 CRUD
6. 短期 Memory
7. 长期 Memory
8. Guardrails
9. MCP Client
10. 餐厅搜索
11. 推荐排序
12. Agent Chat
13. Workflow / LangGraph

14. 前端项目骨架
15. 前端基础布局
16. Chat 对话页面
17. 餐厅推荐卡片
18. 收藏夹页面
19. Memory 偏好面板
20. 前后端联调
21. 测试与部署


step4:用户 bootstrap
设计说明：
app/user_service统一组织用户的初始化
app/user_repository提供用户初始化的相关操作，比如用户创建，
app/schemas/ 目录用于定义基于 Pydantic 的数据模型，
主要负责 API 请求与响应的数据校验、序列化和反序列化。

Schemas 作为系统对外的数据契约（DTO），
用于隔离数据库 ORM 模型与外部接口，
避免直接暴露数据库字段，
从而实现数据解耦与安全控制。

Step 6：短期 Memory
1. 开发目标

短期 Memory 用 Redis 存当前会话上下文。

主要用于支持：

收藏第二家
换一家评分更高的
不要辣的
刚才推荐的第一个是哪家

也就是记录当前对话里的临时状态。

router中的各种方法的作用：


Step 7：长期 Memory 开发
1. 开发目标

长期 Memory 存在 PostgreSQL 的 user_memory 表中，来源于用户收藏夹摘要。

它要实现：
读取用户收藏餐厅
→ 聚合菜系、价格、推荐菜、评论摘要
→ 生成用户偏好
→ 更新 user_memory

长期记忆需要入库postgres，并且需要相应的schema



Step 8：Guardrails 开发
1. 开发目标

Guardrails 是应用层审核模块，位置在：

外部数据 / 用户输入
        ↓
Guardrails
        ↓
Service / Repository / Database

本阶段重点实现两个核心 Guard：

MCPResultGuard
DatabaseWriteGuard
2. 本阶段新增文件
app/guardrails/mcp_result_guard.py
app/guardrails/database_write_guard.py
app/guardrails/text_cleaner.py
app/schemas/guardrail.py
app/api/v1/guardrails.py

修改：

app/api/v1/router.py
3. Guardrails 模块职责
3.1 MCPResultGuard

负责处理 MCP / 外部接口返回的餐厅数据。

能力：

字段白名单过滤
必填字段校验
类型标准化
文本长度限制
JSON 结构清洗
非法字段丢弃
3.2 DatabaseWriteGuard

负责数据库写入前审核。

能力：

收藏餐厅数据入库前校验
空值处理
文本截断
raw_data 白名单过滤
recommended_dishes 标准化
rating / avg_price / distance 类型转换
3.3 TextCleaner

负责文本清洗。

能力：

去除 HTML 标签
去除多余空白
文本截断
去除控制字符

step9:
开发目标
实现：

FastAPI
  ↓
MCPService
  ↓
AmapMCPClient
  ↓
streamable_http_client
  ↓
高德 MCP Server
  ↓
MCPResultGuard
  ↓
标准化结果

本阶段要打通：

1. GET  /api/v1/mcp/tools
2. POST /api/v1/mcp/geocode
3. POST /api/v1/mcp/text-search
4. POST /api/v1/mcp/around-search
5. POST /api/v1/mcp/place-detail
2. 配置项调整
.env
MCP_MODE=remote
AMAP_MCP_URL=https://mcp.amap.com/mcp?key=你的高德地图key
MCP_TIMEOUT_SECONDS=15
app/core/config.py

增加：

MCP_MODE: str = "remote"
AMAP_MCP_URL: str | None = None
MCP_TIMEOUT_SECONDS: int = 15
3. 工具映射设计

根据你测试出来的 tools，建议这样映射：

项目能力	高德 MCP Tool
地址转经纬度	maps_geo
经纬度逆地址	maps_regeocode
城市关键词搜索	maps_text_search
周边搜索	maps_around_search
POI 详情	maps_search_detail
路线规划	maps_direction_*

当前项目第 9 步先做：

maps_geo
maps_text_search
maps_around_search
maps_search_detail
4. 高德 MCP 返回结构特点

你的返回结果是：

result.content[0].text

里面是 JSON 字符串：

{
  "suggestion": {},
  "pois": [
    {
      "id": "B0FFF9XSVV",
      "name": "胡大饭馆24h(簋街总店)",
      "address": "东直门内大街233号",
      "typecode": "050102",
      "photo": "..."
    }
  ]
}

所以 Client 要做：

CallToolResult
→ content[0].text
→ json.loads
→ 提取 pois
→ 标准化为 RestaurantMCPResult
→ MCPResultGuard
5. 本阶段新增 / 修改文件
新增
app/mcp/amap_streamable_client.py
app/mcp/schemas.py
app/services/mcp_service.py
app/api/v1/mcp.py
修改
app/core/config.py
app/api/v1/router.py
.env.example

补充工作：
先补 Step 8 Guardrails 的 photo 白名单
再补 Step 9 MCP normalize 的 photo 输出
这里将MCP转换为代理模式后，需要将mcp的url配置到环境变量中去


Step 10：餐厅搜索服务
1. 开发目标

实现核心接口：

POST /api/v1/restaurants/search

业务链路：

用户输入地址 / 经纬度 / 关键词
        ↓
MCP geocode / around-search / text-search
        ↓
MCPResultGuard 标准化结果
        ↓
读取用户长期 Memory
        ↓
基础排序和推荐理由
        ↓
写入短期 Memory.current_candidates
        ↓
返回餐厅列表
2. 新增文件
app/schemas/restaurant.py
app/services/restaurant_search_service.py
app/api/v1/restaurants.py

修改：

app/api/v1/router.py
3. 本阶段暂不做的事
不做复杂推荐排序
不做 LangGraph
不做 Agent Chat
不做收藏
不做 LLM 推荐

4. 搜索策略
4.1 用户提供 address
address 存在
→ 调用 MCP geocode
→ 得到 location
→ 调用 around-search
4.2 用户直接提供 location
location 存在
→ 直接调用 around-search
4.3 address 和 location 都没有
降级使用 text-search




Step 11：推荐排序 Ranking
1. 开发目标

把推荐排序独立成模块：

餐厅候选列表
+ 用户长期 Memory
+ 当前搜索条件 filters
        ↓
RankingService
        ↓
排序后的餐厅 + score + match_reasons + recommend_reason
2. 新增文件
app/services/ranking_service.py
app/schemas/ranking.py

修改：

app/services/restaurant_search_service.py

可选新增测试接口：

app/api/v1/ranking.py

如果你想先方便测试，可以加；如果不想暴露内部排序接口，也可以只在测试里直接测 RankingService。

3. Ranking 设计
3.1 排序维度
维度	权重
用户偏好菜系匹配	30
当前筛选菜系匹配	20
评分	20
距离	15
价格匹配	10
场景匹配	10
口味关键词匹配	10
推荐菜匹配	5

总分不需要严格归一化，先采用可解释规则分。

3.2 推荐理由

每家餐厅返回：

{
  "score": 78.5,
  "match_reasons": [
    "符合你偏好的菜系：川菜",
    "评分较高：4.7",
    "距离较近：850m",
    "价格符合你的历史偏好"
  ],
  "recommend_reason": "这家店符合你偏好的川菜和偏辣口味，评分较高，距离也较近。"
}



step12开发：
支持用户说：
我在望京SOHO，推荐几家适合朋友聚餐的川菜，人均150以内

Agent 应该调用：

search_restaurants
支持用户说：
收藏第一家

Agent 应该：

读取短期 Memory.current_candidates
找到 rank=1 的餐厅
调用 add_favorite
支持用户说：
我收藏过哪些餐厅？

Agent 应该调用：

show_favorites
支持用户说：
我不吃香菜

先做：

更新短期 Memory

后续再进入长期 Memory 偏好更新。

Step 12 建议新增文件
app/schemas/agent.py
app/agent/tool_registry.py
app/agent/intent_parser.py
app/services/agent_service.py
app/api/v1/agent.py

修改：

app/api/v1/router.py
app/core/config.py
.env.example

我们让LLM调用工具的方式并不是直接调用工具，
把高德mcp提供的工具进行安全封装，然后让LLM调用封装好的工具


Step 13：Workflow / LangGraph。这一阶段要把 Step12 里“单次 AgentService 调工具”的逻辑升级成状态机：先读记忆，再判断意图，再走搜索/收藏/记忆分支，最后统一生成回复。
1. 目标

把现在的：

AgentService
  ├── 判断意图
  ├── 调工具
  └── 生成回复

升级为：

AgentWorkflow
  ├── load_memory
  ├── classify_intent
  ├── route
  ├── search_restaurants
  ├── add_favorite
  ├── show_favorites
  ├── memory_ops
  └── generate_response

LangGraph 的核心是 StateGraph：每个节点读取/更新同一个 state；流程通过普通边或条件边连接。官方文档也建议动态流程用 add_conditional_edges 做路由。

2. 安装依赖

在 backend 环境：

conda activate offerhunter
cd D:\tastescount-agent\backend

pip install langgraph

requirements.txt 增加：

langgraph
3. 新增文件
app/workflows/agent_state.py
app/workflows/agent_workflow.py
app/workflows/nodes.py

修改：

app/services/agent_service.py

可选新增调试接口：

app/api/v1/workflow.py
4. Workflow 路由设计
START
  ↓
load_memory
  ↓
classify_intent
  ↓
route_by_intent
    ├── search_restaurants → generate_response → END
    ├── add_favorite      → generate_response → END
    ├── show_favorites    → generate_response → END
    ├── get_memory        → generate_response → END
    ├── refresh_memory    → generate_response → END
    └── fallback          → generate_response → END

18.1 浏览器定位
→
18.4 推荐去重
→
18.3 多轮追问
→
18.2 地图可视化

完成向SKILL.md的转换
新架构
API 层
只负责 HTTP 入参出参

AgentService
只负责启动 AgentWorkflow

AgentWorkflow
只负责编排节点和路由

AgentWorkflowNodes
只负责通用 Agent 步骤：load memory、classify intent、execute skill、generate response

Skill
负责一个 Agent 能力的参数准备、执行、结果格式化

Service
负责真实业务逻辑：搜索、收藏、记忆刷新、排序

Repository/MCP/Memory
负责数据和外部服务访问