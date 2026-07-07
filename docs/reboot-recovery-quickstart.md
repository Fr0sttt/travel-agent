# 开机后恢复口令

以后你服务器重启完，直接发我这句话就够了：

> `执行服务器开机恢复，按当前项目固定流程把中间件、后端、tunnel 都拉起来，并确认 health`

这句话的意思很明确，我会默认做下面这几步：

1. 先检查服务器是不是刚重启
2. 拉起 PostgreSQL、Elasticsearch
3. 拉起后端
4. 拉起 localtunnel
5. 最后确认 `http://127.0.0.1:8000/health`

## 你额外给我什么最省时间

如果你顺手再贴一条日志，我能更快定位：

```powershell
scripts\watch-server-logs.ps1 -Mode health -NoFollow
```

如果你已经手工点过恢复，再补一条：

```powershell
scripts\watch-server-logs.ps1 -Mode backend -NoFollow
```

## 我会默认执行的脚本

- `scripts/restart-remote-stack.ps1`

## 你不用再解释的内容

下面这些我会默认按当前仓库状态处理，不需要你每次重复说：

- 前端是 GitHub Pages，不走 nginx
- 后端和中间件在远端服务器
- 需要优先恢复 PostgreSQL、Elasticsearch、后端、tunnel
- 线上后端要保持“小红书增强版”那套代码

## 最后一句

你只要发：

> `执行服务器开机恢复`

我就按固定流程接着干。
