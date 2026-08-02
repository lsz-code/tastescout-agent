# TasteScout Agent

TasteScout Agent 是一个面向餐厅发现与个人口味管理的 AI 助手。项目由 Next.js 前端、FastAPI 后端和高德 MCP 代理组成，使用 PostgreSQL 保存业务数据、Redis 保存短期会话，并通过 OpenAI 兼容接口调用大语言模型。

## 功能

- 自然语言搜索和推荐周边餐厅
- 基于位置、菜系、价格等条件进行结果排序
- 收藏餐厅与管理收藏夹
- 保存短期会话和长期口味偏好
- 查看餐厅详情并提交评价
- 高德地图展示与高德 MCP 地点检索

## 项目结构

```text
.
├── amap_mcp_proxy/   # 高德 MCP 到 HTTP API 的适配服务
├── backend/          # FastAPI、LangGraph、数据库模型与迁移
├── frontend/         # Next.js Web 应用
├── .gitignore
└── README.md
```

仓库仅保留本地运行必需的源码、依赖清单、迁移和示例配置。构建缓存、安装后的依赖、日志、演示文档以及域名/证书相关的生产部署文件均不纳入仓库。

## 环境要求

- Python 3.11+
- Node.js 20+ 与 npm
- PostgreSQL 16+
- Redis 7+
- 高德 MCP Key 与高德 Web JS API Key
- 支持 OpenAI 兼容接口的 LLM API Key（默认示例为通义千问）

## 本地启动

### 1. 准备 PostgreSQL 和 Redis

启动 PostgreSQL 与 Redis，并创建数据库：

```sql
CREATE DATABASE tastescout;
```

默认连接地址分别是 `localhost:5432` 和 `localhost:6379`，可在后端环境变量中修改。

### 2. 配置环境变量

PowerShell：

```powershell
Copy-Item backend/.env.example backend/.env
Copy-Item amap_mcp_proxy/.env.example amap_mcp_proxy/.env
Copy-Item frontend/.env.example frontend/.env.local
```

至少需要填写以下值：

- `backend/.env`：`DATABASE_URL`、`POSTGRES_*`、`REDIS_URL`、`LLM_BASE_URL`、`LLM_API_KEY` 和 `LLM_MODEL`
- `amap_mcp_proxy/.env`：带有效 Key 的 `AMAP_MCP_URL`
- `frontend/.env.local`：`NEXT_PUBLIC_AMAP_JS_KEY`

环境文件已被 Git 忽略，请勿提交真实密钥。

### 3. 安装 Python 依赖并迁移数据库

在项目根目录执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python -m pip install -r amap_mcp_proxy/requirements.txt
Set-Location backend
alembic upgrade head
Set-Location ..
```

### 4. 启动三个服务

分别打开三个终端。

高德 MCP 代理：

```powershell
Set-Location amap_mcp_proxy
uvicorn main:app --reload --port 8010
```

后端：

```powershell
Set-Location backend
uvicorn app.main:app --reload --port 8000
```

前端：

```powershell
Set-Location frontend
npm ci
npm run dev
```

打开 <http://localhost:3000> 即可使用。后端接口文档位于 <http://localhost:8000/docs>。

## 健康检查

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
Invoke-RestMethod http://127.0.0.1:8010/health
```

## 开发检查

```powershell
python -m compileall -q backend/app backend/alembic amap_mcp_proxy
Set-Location frontend
npm run build
```

## API 概览

后端 API 统一使用 `/api/v1` 前缀，主要模块包括：

- `/agent`：AI 对话与工具调用
- `/restaurants`：餐厅与评价
- `/favorites`、`/favorite-collections`：收藏管理
- `/memory`：短期与长期记忆
- `/mcp`：高德检索代理

详细请求和响应结构以启动后的 Swagger 文档为准。
