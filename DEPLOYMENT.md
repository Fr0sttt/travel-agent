# 部署方案

## 目标

- 前端：GitHub Pages
- 后端：你自己的服务器
- 中间件：PostgreSQL、Elasticsearch、MCP 都放在服务器上

## 前端

1. 复制 `app/.env.production.example`。
2. 把 `VITE_API_BASE` 改成你的后端地址，例如 `https://api.xxx.com`。
3. 把 `VITE_AMAP_KEY` 换成你自己的高德 JSAPI Key。
4. 发布时把 `VITE_ROUTER_MODE` 保持为 `hash`，这样 GitHub Pages 刷新子路由不会 404。

## 后端

1. 复制 `travel-agent/backend/.env.production.example`。
2. 把 `CORS_ORIGINS` 改成你的 GitHub Pages 域名和自定义域名。
3. 让 PostgreSQL 和 Elasticsearch 在服务器本机或内网可达。
4. `REMOTE_MIDDLEWARE_SSH_ENABLED=false` 时，后端直接连服务器上的中间件，不再走本机 SSH 隧道。

## GitHub Pages

- 构建目录是 `app/dist`
- 构建命令是 `npm run build`
- 线上路由模式用 `hash`

## 你现在只要关心的值

- `VITE_API_BASE`
- `VITE_AMAP_KEY`
- `CORS_ORIGINS`
- `SESSION_HISTORY_DB_URL`
- `ELASTICSEARCH_URL`
