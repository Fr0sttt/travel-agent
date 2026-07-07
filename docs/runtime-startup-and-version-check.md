# 运行启动与版本核对

这份文档只讲三件事：

1. 现在服务器怎么起
2. 前端怎么发布
3. 怎么确认当前线上后端是不是小红书增强版

## 一、当前运行结构

### 前端

- 源码目录：`app/`
- 发布方式：GitHub Pages
- 发布工作流：`.github/workflows/deploy-pages.yml`

前端不是靠服务器上的 nginx 启动的。  
它走的是 GitHub Pages，页面里通过 `VITE_API_BASE` 去请求后端。

### 后端

- 运行目录：`/root/rivermind-data/travel-agent/backend`
- 入口：`app/main.py`
- 监听端口：`8000`

### 中间件

- PostgreSQL：`5432`
- Elasticsearch：`9200`
- 本地 tunnel：`https://eight-donkeys-begin.loca.lt`

## 二、启动顺序

服务器重启后，按这个顺序恢复：

1. PostgreSQL
2. Elasticsearch
3. 后端 API
4. 本地 tunnel

其中：

- PostgreSQL 用 `pg_ctl` 拉起
- Elasticsearch 用 1G 堆内存启动，避免默认 8G 堆太重
- 后端用 `setsid -f ... python app/main.py` 启动，避免 SSH 断开后退出
- tunnel 用 `npx localtunnel --port 8000 --subdomain eight-donkeys-begin`

## 三、一键恢复脚本

本地脚本：

- `scripts/restart-remote-stack.ps1`

它会：

1. 通过 SSH 连到服务器
2. 重启 PostgreSQL / Elasticsearch / 后端
3. 等待 `5432`、`9200`、`8000` 恢复

## 四、怎么判断是不是小红书增强版

线上后端必须同时满足这几条：

1. 服务器目录里有 `app/agent/guide_search.py`
2. `app/agent/graph.py` 里接了 `search_guide_pois(...)`
3. `app/config.py` 里有 `JUSTONEAPI_*` 和 `DEEPSEEK_*` 配置
4. 服务器 `.env` 里打开了：
   - `JUSTONEAPI_ENABLED=true`
   - `DEEPSEEK_ENABLED=true`
5. 服务器 `.env` 里有小红书访问 key

## 五、当前线上核对结果

我已经核对过当前服务器：

- `guide_search.py` 已同步到服务器
- `graph.py` 已同步到服务器
- `config.py` 已同步到服务器
- 服务器 `.env` 已写入：
  - `JUSTONEAPI_ENABLED=true`
  - `JUSTONEAPI_KEY=...`
  - `DEEPSEEK_ENABLED=true`

这意味着，当前线上跑的后端已经切到小红书增强版本，不再是旧的纯地图版本。

## 六、验证方法

### 1. 看健康接口

```bash
curl http://127.0.0.1:8000/health
```

### 2. 看服务端口

```bash
ss -ltnp | egrep ':5432|:9200|:8000'
```

### 3. 看文件哈希

```bash
sha256sum /root/rivermind-data/travel-agent/backend/app/agent/guide_search.py
sha256sum /root/rivermind-data/travel-agent/backend/app/agent/graph.py
sha256sum /root/rivermind-data/travel-agent/backend/app/config.py
```

### 4. 看前端请求地址

GitHub Pages 页面必须指向：

- `https://eight-donkeys-begin.loca.lt`

如果页面还在请求旧地址，就会看起来像“后端没启动”，但本质其实是前端配置还没对上。

