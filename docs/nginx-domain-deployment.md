# TasteScout Nginx 反向代理部署说明

## 一键启动

生产环境统一使用项目根目录的 `docker-compose.prod.yml`：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

这个命令会启动：

- PostgreSQL
- Redis
- Amap MCP Proxy
- FastAPI Backend
- Next.js Frontend
- Nginx Reverse Proxy

公网只需要访问 Nginx 的 `80/443`，后端和前端通过 Docker 内网访问。

## 证书和密钥文件位置

在服务器项目根目录创建：

```bash
mkdir -p deploy/nginx/certs/live/www.tastescout-agent.xin
```

然后把 HTTPS 证书和私钥放到：

```text
deploy/nginx/certs/live/www.tastescout-agent.xin/fullchain.pem
deploy/nginx/certs/live/www.tastescout-agent.xin/privkey.pem
```

其中：

- `fullchain.pem` 是证书链文件。
- `privkey.pem` 是私钥文件。

`privkey.pem` 不能提交到 Git，也不要打进镜像。

容器内路径对应 `.env.prod`：

```env
NGINX_SSL_CERTIFICATE=/etc/letsencrypt/live/www.tastescout-agent.xin/fullchain.pem
NGINX_SSL_CERTIFICATE_KEY=/etc/letsencrypt/live/www.tastescout-agent.xin/privkey.pem
```

## 使用 Certbot 辅助申请证书

如果你没有证书，可以使用 Compose 里的 `certbot` 服务申请。这个服务使用 standalone 模式，会临时占用服务器 `80` 端口。

先确认：

- DNS 已指向 `47.116.25.59`
- 服务器安全组已开放 `80/tcp`
- `.env.prod` 已配置 `PUBLIC_DOMAIN` 和 `CERTBOT_EMAIL`
- Nginx 当前没有占用 `80` 端口；如果已经启动了 Nginx，先执行 `docker compose -f docker-compose.prod.yml --env-file .env.prod stop nginx`

执行：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod run --rm --service-ports certbot
```

Certbot 会把证书写入：

```text
deploy/nginx/certs/live/www.tastescout-agent.xin/
```

证书生成后再启动完整服务：

```bash
docker compose -f docker-compose.prod.yml --env-file .env.prod up -d --build
```

## 访问路径

```text
https://www.tastescout-agent.xin/
  -> frontend:3000

https://www.tastescout-agent.xin/api/v1/...
  -> backend:8000
```

## 验证

```bash
docker compose -f docker-compose.prod.yml logs -f nginx
curl -I https://www.tastescout-agent.xin/
curl -I https://www.tastescout-agent.xin/api/v1/health
```
