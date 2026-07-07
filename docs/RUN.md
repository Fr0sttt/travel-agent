# Travel Agent 项目启动运行指南

## 一、项目结构

```
多agent旅行代理全栈实现/
├── app/                          # 前端（React + Vite + TypeScript）
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       └── ...
├── travel-agent/
│   └── backend/                  # 后端（FastAPI + LangGraph + Python）
│       ├── requirements.txt
│       ├── .env                  # 环境变量配置文件
│       └── app/
│           ├── main.py           # FastAPI 入口
│           └── config.py         # 配置管理
└── docs/
    └── RUN.md                    # 本文档
```

---

## 二、环境要求

| 组件 | 版本要求 |
|---|---|
| Python | **>= 3.10**（推荐 3.11，3.9 会因类型注解语法 `\|` 报错） |
| Node.js | >= 18（推荐 LTS） |
| npm | >= 9 |

> 本机已验证环境：Python 3.11、Node v25.9.0、npm 11.12.1

---

## 三、后端启动步骤

### 1. 进入后端目录

```bash
cd travel-agent/backend
```

### 2. 创建虚拟环境（使用 Python 3.11）

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
```

> 如果你的系统没有 `python3.11`，请确保 Python 版本 >= 3.10。  
> 使用系统默认 Python 3.9 会导致启动失败（`TypeError: unsupported operand type(s) for |: 'type' and 'NoneType'`）。

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

后端已提供 `.env` 文件，位于：

```
travel-agent/backend/.env
```

核心配置项：

```env
# Kimi OpenAI 兼容接口
OPENAI_API_KEY=
OPENAI_BASE_URL=https://api.kimi.com/coding/
OPENAI_MODEL=kimi-k2-0711-preview
OPENAI_TIMEOUT=120

# 运行环境
APP_ENV=development
DEBUG=true
LOG_LEVEL=INFO

# 可选：OpenTripMap 真实景点数据（留空使用 demo 数据）
OPENTRIPMAP_API_KEY=

# 可选：Langfuse 观测（留空禁用）
LANGFUSE_PUBLIC_KEY=
LANGFUSE_SECRET_KEY=
LANGFUSE_ENABLED=false

# FastAPI 服务地址
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

> Kimi API 兼容 OpenAI SDK，因此只需修改 `OPENAI_BASE_URL` 和 `OPENAI_API_KEY` 即可，无需改动业务代码。

### 5. 启动后端服务

```bash
cd app
python main.py
```

或者使用 uvicorn：

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

启动成功后输出：

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

### 6. 验证后端

```bash
curl http://localhost:8000/health
```

预期返回：

```json
{
  "status": "ok",
  "version": "1.0.0",
  "dependencies": {
    "langgraph": "ok",
    "tools": "7 tools loaded",
    "openai": "configured",
    "opentripmap": "not configured (using demo data)",
    "langfuse": "not configured"
  }
}
```

- API 文档：[http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc：[http://localhost:8000/redoc](http://localhost:8000/redoc)

---

## 四、前端启动步骤

### 1. 进入前端目录

```bash
cd app
```

> 注意：前端目录在项目根目录的 `app/`，不是 `travel-agent/frontend/`。

### 2. 安装依赖

```bash
npm install
```

> 如果之前安装失败或 `package-lock.json` 指向了失效镜像（如 `npm.mirrors.msh.team`），请先清理：
>
> ```bash
> rm -rf node_modules package-lock.json
> npm install
> ```

### 3. 启动开发服务器

```bash
npm run dev
```

启动成功后输出：

```
VITE v7.3.5  ready in XXX ms

➜  Local:   http://localhost:3000/
```

### 4. 验证前端

浏览器打开：[http://localhost:3000](http://localhost:3000)

---

## 五、主要 API 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查 |
| GET | `/` | API 信息 |
| POST | `/api/plan` | 创建行程规划（同步） |
| POST | `/api/plan/stream` | 创建行程规划（SSE 流式） |
| GET | `/api/plan/{session_id}` | 获取规划结果 |
| DELETE | `/api/plan/{session_id}` | 删除会话 |
| POST | `/api/chat` | 聊天接口（同步） |
| POST | `/api/chat/stream` | 聊天接口（SSE 流式） |
| WS | `/ws/chat/{session_id}` | WebSocket 实时对话 |
| GET | `/api/tools` | 可用工具列表 |

---

## 六、常见问题

### 1. Python 3.9 启动报错：`TypeError: unsupported operand type(s) for |`

**原因**：代码中使用了 Python 3.10+ 的类型注解语法（如 `dict | None`），而 LangChain 在创建工具时会解析这些注解。

**解决**：使用 Python 3.10 或 3.11 重新创建虚拟环境。

```bash
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. FastAPI 报错：`Invalid args for response field! TravelAgent`

**原因**：`main.py` 中使用了 `agent: TravelAgent = get_agent` 这种非标准依赖注入写法，新版 FastAPI 无法识别。

**解决**：已修复为标准 `Depends(get_agent)`。如果仍遇到，请确保代码中的参数写法为：

```python
from fastapi import Depends

async def create_plan(
    request: PlanRequest,
    agent: TravelAgent = Depends(get_agent),
) -> AgentResponse:
```

### 3. 后端启动后 `/health` 显示 `openai: not configured`

**原因**：`.env` 文件没有被加载。`config.py` 原先用的是相对路径 `.env`，如果从 `app/` 子目录启动会找不到文件。

**解决**：已修复为绝对路径定位 `.env`（基于 `config.py` 所在目录）。确保 `.env` 位于 `travel-agent/backend/.env`。

### 4. 前端 `npm install` 失败，日志中出现 `npm.mirrors.msh.team`

**原因**：`package-lock.json` 中的 `resolved` 字段指向了已失效的私有镜像。

**解决**：删除锁文件重新安装：

```bash
rm -rf node_modules package-lock.json
npm install
```

### 5. 端口冲突

如果 8000 或 3000 端口被占用：

```bash
# 释放 8000 端口
lsof -ti:8000 | xargs kill -9

# 释放 3000 端口
lsof -ti:3000 | xargs kill -9
```

---

## 七、前后端联调说明

目前前端 (`app/src`) 主要使用 mock 数据展示界面，尚未实际调用后端 API。后端 CORS 已默认放行 `http://localhost:3000`，因此联调时只需在前端增加 API 请求即可。

示例：在 `app/src/lib/api.ts` 中封装：

```ts
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function createPlan(input: string) {
  const res = await fetch(`${API_BASE}/api/plan`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_input: input }),
  });
  return res.json();
}
```

并在 `app/.env` 中配置：

```env
VITE_API_BASE=http://localhost:8000
```

---

## 八、启动速查

```bash
# 终端 1：启动后端
cd travel-agent/backend
source .venv/bin/activate
cd app
python main.py

# 终端 2：启动前端
cd app
npm run dev
```

访问：

- 前端：[http://localhost:3000](http://localhost:3000)
- 后端：[http://localhost:8000](http://localhost:8000)
- 后端文档：[http://localhost:8000/docs](http://localhost:8000/docs)
- 健康检查：[http://localhost:8000/health](http://localhost:8000/health)
