# 启动总览与版本确认

这是一份给自己看的总控说明，目标只有两个：

1. 任何时候都能把整套服务按正确顺序拉起来
2. 能快速判断线上后端是不是已经切到“小红书增强版”

## 1. 当前架构

### 前端

- 目录：`app/`
- 发布方式：GitHub Pages
- 发布工作流：`.github/workflows/deploy-pages.yml`
- 运行时依赖：`VITE_API_BASE`、`VITE_AMAP_KEY`、`VITE_AMAP_SECURITY_JS_CODE`

前端不是靠服务器上的 nginx 起的，GitHub Pages 才是最终入口。

### 后端

- 运行目录：`/root/rivermind-data/travel-agent/backend`
- 启动入口：`app/main.py`
- 健康检查：`http://127.0.0.1:8000/health`

### 中间件

- PostgreSQL：`5432`
- Elasticsearch：`9200`
- 远端数据盘根目录：`/root/rivermind-data`

## 2. 推荐启动顺序

服务器重启后，按这个顺序恢复：

1. PostgreSQL
2. Elasticsearch
3. 后端 API
4. 本地 tunnel
5. 再打开 GitHub Pages 前端

后端和中间件都在服务器上，前端在 GitHub Pages 上。

## 3. 一键恢复

本地直接用：

- `scripts/restart-remote-stack.ps1`

它会通过 SSH 连到服务器，然后按顺序重启 PostgreSQL、Elasticsearch 和后端，并等待健康检查恢复。

## 4. 怎么确认是“小红书增强版”

线上后端至少要满足下面这几个信号：

1. 服务器上存在 `app/agent/guide_search.py`
2. `app/agent/graph.py` 里已经接入 `search_guide_pois(...)`
3. `app/config.py` 里有 `JUSTONEAPI_*` 和 `DEEPSEEK_*` 配置
4. 服务器 `.env` 里打开了 `JUSTONEAPI_ENABLED=true`
5. 服务器 `.env` 里打开了 `DEEPSEEK_ENABLED=true`

如果这几条都成立，说明线上跑的就不是旧的纯地图版本，而是已经接入小红书攻略搜索的版本。

## 5. 当前核对结论

我已经把本地的以下文件同步到服务器，并且远端与本地的 SHA256 指纹一致：

- `travel-agent/backend/app/agent/guide_search.py`
- `travel-agent/backend/app/agent/graph.py`
- `travel-agent/backend/app/config.py`

同时，服务器侧 `.env` 已开启：

- `JUSTONEAPI_ENABLED=true`
- `DEEPSEEK_ENABLED=true`

远端 `http://127.0.0.1:8000/health` 也已经返回 `ok`。

换句话说，当前部署启动后的后端，已经是我们改过的小红书版，不是旧的纯地图版本。

## 6. 快速验证

### 看后端是否活着

```bash
curl http://127.0.0.1:8000/health
```

### 看端口是否都起来了

```bash
ss -ltnp | egrep ':5432|:9200|:8000'
```

### 看 xhs 代码是否在位

- `travel-agent/backend/app/agent/guide_search.py`
- `travel-agent/backend/app/agent/graph.py`
- `travel-agent/backend/app/config.py`

## 7. 详细说明

如果要看更完整的恢复过程和前端发布方式，继续看：

- [server-recovery-and-deployment.md](./server-recovery-and-deployment.md)
- [runtime-startup-and-version-check.md](./runtime-startup-and-version-check.md)
