# 服务器开机自启

这份说明记录的是“服务器重启后，哪些服务会自己起来”的固定流程。

## 现在的状态

仓库里已经有两类脚本：

1. 手动恢复用：`scripts/restart-remote-stack.ps1`
2. 开机自启安装用：`scripts/install-server-autostart.ps1`

其中，远端已经存在的中间件启动脚本是：

- `/opt/travel-middleware/start-middleware.sh`

它负责把 PostgreSQL、Elasticsearch、Redis 拉起来。

## 开机自启做了什么

安装脚本会在服务器上创建两样东西：

1. 一个常驻的 bootstrap 守护脚本
2. 一个 systemd 服务

这个守护脚本会持续检查并维持下面这些服务：

- 中间件：PostgreSQL、Elasticsearch
- 后端：FastAPI / LangGraph 服务
- 对外通道：localtunnel

## 为什么需要它

之前的恢复流程依赖手动执行，服务器重启后容易漏掉某个环节，最常见的是：

- PostgreSQL 起来了，但 Elasticsearch 没起来
- 后端起来了，但 tunnel 没起来
- tunnel 起来了，但后端还没就绪

现在这套自启脚本把这几个环节串成了固定顺序，并且会持续巡检，避免只起一半。

## 本地怎么安装

运行：

```powershell
scripts\install-server-autostart.ps1
```

默认会连接到当前项目已经在用的服务器配置。

## 远端会生成什么

- `/root/rivermind-data/travel-agent/bin/travel-agent-autostart.sh`
- `/etc/systemd/system/travel-agent-autostart.service`

## 验证方式

在服务器上看服务状态：

```bash
systemctl status travel-agent-autostart.service
```

看监听端口：

```bash
ss -ltnp | egrep ':5432|:9200|:8000'
```

看健康检查：

```bash
curl http://127.0.0.1:8000/health
```

## 手动恢复和开机自启的关系

- 开机自启：负责平时“自动兜住”
- `restart-remote-stack.ps1`：负责你需要手动拉一遍的时候“一键恢复”

两者是配套的，不冲突。
