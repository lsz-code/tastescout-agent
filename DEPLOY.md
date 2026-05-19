# TasteScout Agent Docker 部署说明

本文档用于在 Linux 服务器上用 Docker Compose 一键部署 TasteScout Agent。

## 1. 上传项目

将完整项目目录上传到服务器，例如：

```bash
/opt/tastescount-agent
```

进入项目根目录：

```bash
cd /opt/tastescount-agent
```

服务器只需要安装 Docker 和 Docker Compose 插件，不需要提前安装 Python、Node.js、PostgreSQL 或 Redis。后端、前端、MCP Proxy、数据库和缓存都会由 Docker 镜像与 Compose 服务提供。

## 2. 准备环境变量

复制生产环境变量模板：

```bash
cp .env.prod.example .env.prod
```

编辑 `.env.prod`，至少修改以下配置：

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `SYNC_DATABASE_URL`
- `AMAP_MCP_URL`
- `LLM_API_KEY`
- `NEXT_PUBLIC_API_BASE_URL`
- `NEXT_PUBLIC_AMAP_JS_KEY`

说明：

- 阿里云服务器如果构建 Python 镜像时无法访问 PyPI，可以保留默认的 pip 镜像配置：
  - `PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/`
  - `PIP_TRUSTED_HOST=mirrors.aliyun.com`
- `AMAP_MCP_URL` 使用高德 MCP Key，例如 `https://mcp.amap.com/mcp?key=你的高德MCPKey`
- `NEXT_PUBLIC_AMAP_JS_KEY` 使用高德 Web 端 JS API Key
- Docker 内部服务地址使用 Compose 服务名：
  - PostgreSQL：`postgres:5432`
  - Redis：`redis:6379`
  - Amap MCP Proxy：`http://amap-mcp-proxy:8010`
- 如果直接暴露后端 8000 端口，`NEXT_PUBLIC_API_BASE_URL` 可以配置为：

```bash
http://你的服务器IP:8000/api/v1
```

如果后续通过 Nginx 代理，可以改成：

```bash
https://你的域名/api/v1
```

## 3. 启动服务

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

启动后会自动创建并启动：

- PostgreSQL
- Redis
- Amap MCP Proxy
- FastAPI Backend
- Next.js Frontend

Backend 容器启动时会先执行：

```bash
alembic upgrade head
```

然后再启动 FastAPI。

### 阿里云服务器 Docker Hub 拉取超时

如果在阿里云服务器上遇到类似错误：

```bash
failed to resolve reference "docker.io/library/redis:7-alpine"
dial tcp ...:443: i/o timeout
```

说明服务器访问 Docker Hub 超时，需要配置 Docker 镜像加速器。

推荐做法是在阿里云控制台获取你自己的镜像加速器地址：

1. 登录阿里云控制台
2. 进入“容器镜像服务 ACR”
3. 找到“镜像工具”或“镜像加速器”
4. 复制专属加速器地址，格式通常类似：

```bash
https://xxxxxx.mirror.aliyuncs.com
```

然后在服务器上配置 Docker daemon：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json > /dev/null <<'EOF'
{
  "registry-mirrors": [
    "https://你的阿里云镜像加速器地址"
  ]
}
EOF
sudo systemctl daemon-reload
sudo systemctl restart docker
```

验证 Docker 是否恢复：

```bash
sudo docker info | grep -A 5 "Registry Mirrors"
```

然后重新部署：

```bash
sudo docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

## 4. 查看日志

查看后端日志：

```bash
docker compose -f docker-compose.prod.yml logs -f backend
```

查看高德 MCP Proxy 日志：

```bash
docker compose -f docker-compose.prod.yml logs -f amap-mcp-proxy
```

查看前端日志：

```bash
docker compose -f docker-compose.prod.yml logs -f frontend
```

查看全部服务日志：

```bash
docker compose -f docker-compose.prod.yml logs -f
```

## 5. 访问服务

前端：

```bash
http://你的服务器IP:3000
```

后端 Swagger：

```bash
http://你的服务器IP:8000/docs
```

Amap MCP Proxy 健康检查：

```bash
http://你的服务器IP:8010/health
```

## 6. 停止服务

```bash
docker compose -f docker-compose.prod.yml down
```

## 7. 清空数据

如果需要同时删除 PostgreSQL 和 Redis 数据卷：

```bash
docker compose -f docker-compose.prod.yml down -v
```

该命令会清空收藏、记忆、会话缓存和数据库数据，请谨慎使用。

## 8. 常见检查项

如果前端无法调用 Agent：

- 检查 `.env.prod` 中的 `NEXT_PUBLIC_API_BASE_URL`
- 检查服务器安全组是否开放 8000 和 3000 端口
- 检查后端日志是否有数据库、Redis 或 LLM 配置错误

如果 Agent 无法调用高德 MCP：

- 检查 `.env.prod` 中的 `AMAP_MCP_URL`
- 检查 Amap MCP Proxy 日志
- 确认 `AMAP_MCP_PROXY_URL=http://amap-mcp-proxy:8010`

如果地图无法显示：

- 检查 `.env.prod` 中的 `NEXT_PUBLIC_AMAP_JS_KEY`
- 确认使用的是高德 Web 端 JS API Key，不是后端 MCP Key

如果后端或 MCP Proxy 构建时报：

```bash
ERROR: Could not find a version that satisfies the requirement fastapi
ERROR: No matching distribution found for fastapi
```

通常不是依赖不存在，而是容器构建阶段访问 PyPI 失败。项目已在 `backend/Dockerfile` 和 `amap_mcp_proxy/Dockerfile` 中支持 pip 镜像源，确认 `.env.prod` 中保留：

```bash
PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
PIP_TRUSTED_HOST=mirrors.aliyun.com
```

然后重新构建：

```bash
sudo docker compose -f docker-compose.prod.yml --env-file .env.prod build --no-cache backend amap-mcp-proxy
sudo docker compose -f docker-compose.prod.yml --env-file .env.prod up -d
```
