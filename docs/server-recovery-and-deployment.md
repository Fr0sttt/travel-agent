# 服务器恢复与部署说明

这份说明记录了本项目当前的线上运行方式，以及服务器重启后的恢复顺序，方便后续直接照着做，不用再靠记忆临时拼。

## 一、当前部署拓扑

### 1. 前端

- 源码目录：`app/`
- 发布方式：GitHub Pages
- 发布工作流：`.github/workflows/deploy-pages.yml`
- 构建输出：`app/dist`

前端不是靠服务器上的 nginx “启动”的，而是通过 GitHub Pages 独立发布。  
所以当你问“前端怎么没起来”时，先确认 GitHub Pages 是否已经完成部署，而不是去服务器上找 nginx 进程。

### 2. 后端与中间件

后端和中间件运行在服务器上，数据盘目录是：

- `/root/rivermind-data/travel-agent/backend`
- `/root/rivermind-data/travel-middleware`

依赖顺序：

1. PostgreSQL
2. Elasticsearch
3. 后端 API

## 二、今天实际恢复过的流程

服务器重启后，Docker 守护进程不可用，所以没有走 compose，而是直接在宿主机上恢复了现有服务。

恢复顺序如下：

1. 清理 PostgreSQL 的旧 `postmaster.pid`
2. 使用 `pg_ctl` 启动 PostgreSQL
3. 用更小的堆内存参数启动 Elasticsearch
4. 用 `setsid` 启动后端，避免 SSH 断开后进程退出
5. 通过健康接口确认服务已经可用

## 三、关键检查点

### PostgreSQL

- 端口：`5432`
- 健康检查：`pg_isready -h 127.0.0.1 -p 5432 -U travel -d travel_agent`
- 数据目录：`/root/rivermind-data/travel-middleware/postgres`

### Elasticsearch

- 端口：`9200`
- 健康检查：`curl http://127.0.0.1:9200`
- 启动参数建议使用较小堆内存：
  - `ES_JAVA_OPTS=-Xms1g -Xmx1g`

### 后端

- 端口：`8000`
- 健康检查：`curl http://127.0.0.1:8000/health`
- 启动方式：`setsid -f bash -lc 'cd ... && exec .venv/bin/python app/main.py'`

## 四、前端到底怎么发布

前端使用 GitHub Pages，不依赖服务器 nginx。

`deploy-pages.yml` 的核心逻辑是：

1. 拉代码
2. 进入 `app/`
3. `npm ci`
4. `npm run build`
5. 上传 `app/dist`
6. 发布到 GitHub Pages

前端运行时需要的环境变量：

- `VITE_ROUTER_MODE=hash`
- `VITE_API_BASE`
- `VITE_AMAP_KEY`
- `VITE_AMAP_SECURITY_JS_CODE`

## 五、以后服务器重启时的推荐顺序

1. 先执行远端服务恢复脚本
2. 等 `5432`、`9200`、`8000` 都起来
3. 再打开 GitHub Pages 前端
4. 如需看服务状态，用 `scripts/watch-server-logs.ps1`

## 六、备注

- 如果你看到 nginx 相关内容，那只是“服务器静态站点”路径，不等于 GitHub Pages 前端。
- 当前项目更推荐把前端视作独立发布，把后端和中间件视作服务器常驻服务。

