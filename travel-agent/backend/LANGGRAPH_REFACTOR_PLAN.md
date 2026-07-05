# LangGraph 图引擎接入 + 意图路由改造方案

状态：方案已完成环境验证，待评阅，未开始实施代码改动。

## 一、现状问题

`agent/graph.py` 的 `build_travel_graph()` 定义了完整的 `StateGraph`（9 个节点 + 2 个条件边），
`travel_graph = build_travel_graph()` 在模块加载时编译成全局单例。

但 `agent/travel_agent.py` 的 `TravelAgent.plan_travel` 方法**完全没有调用这个图**：

```python
self.graph = travel_graph   # 赋值了，但后面从未被调用
...
node_sequence = [("preference_collector", "..."), ...]
for node_name, status_msg in node_sequence:
    node_func = self._get_node_function(node_name)
    current_state = await node_func(current_state)   # 手动调用，绕开图引擎
```

后果：
1. 状态全靠 `self.sessions: dict` 纯内存管理，进程重启状态丢失，无断点续传
2. 意图判断靠字符串前缀 `message.startswith("新规划")` 和状态字段手写分支，脆弱且分散
3. `chat()` 和 `plan_travel()` 两套独立入口，逻辑不一致

## 二、环境验证结果（今天已实测，非推测）

| 项目 | 结果 |
|---|---|
| `langgraph` 版本 | 1.2.7（base 环境，`D:\Anaconda\Lib\site-packages`） |
| `langgraph-checkpoint-postgres` | 未安装 → 已装，版本 3.1.0 |
| `psycopg`（v3） | 3.3.4，是 `langgraph-checkpoint-postgres` 的依赖，自动装上 |
| `psycopg2` | 项目现有代码用它连 SQLAlchemy（`pip show` 查不到但能 import，是 `psycopg2-binary`） |
| 两个驱动共存 | **不冲突**。`import psycopg` 和 `import psycopg2` 是两个独立包，SQLAlchemy 继续走 psycopg2，checkpointer 直接用 psycopg v3 原生连接，互不干扰 |

真实 API 签名（已用 `help()` 验证，不是文档推测）：

```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 类方法，返回异步上下文管理器（不是直接返回实例！）
AsyncPostgresSaver.from_conn_string(
    conn_string: str,
    *,
    pipeline: bool = False,
    serde: SerializerProtocol | None = None,
) -> AsyncIterator[AsyncPostgresSaver]

# 实例方法，无参数，自动建表+迁移，首次使用必须手动调用一次
async def setup(self) -> None
```

**关键纠正**：昨天的草案方案里写的 `sync_connection_string`、`table_name`、`threads_table_name` 参数全是编造的，真实 API 只有 `conn_string`/`pipeline`/`serde` 三个参数，且必须用 `async with` 语法，不能直接 `await` 出一个实例。

## 三、目标架构

```
入口: intent_router (新增节点，LLM 分类意图)
  │
  ├─ new_plan ────────→ preference_collector → constraint_normalizer → destination_search
  │                      → route_planner → weather_advisor → budget_estimator
  │                      → itinerary_synthesizer → safety_reviewer → output_formatter → END
  │                      (以上节点函数全部原样复用，不改签名)
  │
  ├─ continue_clarify ─→ preference_collector (复用同一节点，合并 current_pref)
  │
  ├─ faq_about_itinerary → qa_responder (新增节点) → END
  │
  └─ chitchat ─────────→ chitchat_responder (新增节点) → END
```

`preference_collector` 之后的 `should_clarify` 条件边（graph.py:976）和 `safety_reviewer` 之后的
`safety_check` 条件边（graph.py:1014）**原样保留，不需要改**。

## 四、具体改动清单

### 1. `requirements.txt`
```diff
- langgraph>=0.1.0
+ langgraph>=1.2.0,<2.0.0
+ langgraph-checkpoint-postgres==3.1.0
```
风险：锁定 `langgraph-checkpoint-postgres` 精确版本，避免未来自动升级到 API 不兼容的版本。

### 2. `agent/graph.py`

**2.1 `TravelState.create()` 加字段**（约第90-112行的 dict 字面量里追加，`TravelState` 是 dict
子类，不能用 dataclass 语法加字段，必须在这里加 key）：
```python
"user_intent": None,       # new_plan | continue_clarify | faq_about_itinerary | chitchat
"qa_response": None,
"chitchat_response": None,
```

**2.2 新增 `intent_router` 节点函数**（放在 `preference_collector` 定义之前）：
- 输入：`state["user_input"]`、`state.get("itinerary")`、`state.get("needs_clarification")`
- 调用新工具函数 `classify_intent`（第4步定义），LLM 超时/异常时降级到启发式规则：
  - `needs_clarification=True` → `continue_clarify`
  - 有 `itinerary` 且输入包含疑问词（"吗/呢/怎么/如何/为什么"）→ `faq_about_itinerary`
  - 命中"去/想去/规划/旅游/旅行"等关键词 → `new_plan`
  - 否则 → `chitchat`
- 输出：`state["user_intent"] = intent`

**2.3 新增 `qa_responder` 节点函数**：
- 输入：`state["user_input"]`、`state["itinerary"]`、`state.get("weather")`、`state.get("total_budget_estimate")`
- 调用新工具函数 `answer_itinerary_question`，把已有行程内容和用户问题一起给 LLM，直接生成回答
- 输出：追加到 `state["messages"]`，`state["qa_response"] = answer`

**2.4 新增 `chitchat_responder` 节点函数**：
- 输入：`state["user_input"]`
- 调用新工具函数 `generate_chitchat_reply`
- 输出：追加到 `state["messages"]`，`state["chitchat_response"] = reply`

**2.5 改造 `build_travel_graph()`**（第1032行起）：
```python
def build_travel_graph(checkpointer=None) -> CompiledStateGraph:
    workflow = StateGraph(TravelState)

    workflow.add_node("intent_router", intent_router)
    workflow.add_node("qa_responder", qa_responder)
    workflow.add_node("chitchat_responder", chitchat_responder)
    workflow.add_node("preference_collector", preference_collector)
    # ... 其余 8 个既有节点原样 add_node，不改 ...

    workflow.set_entry_point("intent_router")   # 从 preference_collector 改这里

    workflow.add_conditional_edges(
        "intent_router",
        lambda state: state.get("user_intent", "new_plan"),
        {
            "new_plan": "preference_collector",
            "continue_clarify": "preference_collector",
            "faq_about_itinerary": "qa_responder",
            "chitchat": "chitchat_responder",
        },
    )

    # 既有条件边和线性边原样保留：
    workflow.add_conditional_edges("preference_collector", should_clarify, {...})
    workflow.add_edge("constraint_normalizer", "destination_search")
    # ... 全部不变 ...

    workflow.add_edge("qa_responder", END)
    workflow.add_edge("chitchat_responder", END)

    return workflow.compile(checkpointer=checkpointer)
```

**2.6 删除模块级单例**：
```diff
- travel_graph = build_travel_graph()
```
原因：checkpointer 只有在 `main.py` 的 `lifespan` 里拿到真实 PG 连接后才存在，图必须延迟到那时才编译，不能在模块加载时就编译成不带 checkpointer 的单例。

风险：任何其他文件如果 `from agent.graph import travel_graph` 会报错，需要搜索确认没有其他引用点（已搜索，只有 `agent/__init__.py` 和 `travel_agent.py` 引用，两处都会在第5步一起改）。

### 3. `agent/prompts.py`（文件末尾追加）

三段新 prompt：`INTENT_CLASSIFICATION_PROMPT`、`QA_ANSWER_PROMPT`、`CHITCHAT_PROMPT`。
内容需要用中文场景例句（复用今天已验证的失败案例，比如"上海3天预算1000"这种无分隔符表达），
不是泛泛的英文模板翻译。分类 prompt 要求 LLM 输出严格 JSON：`{"intent": "...", "confidence": 0-1}`。

### 4. `agent/tools.py`（文件末尾追加）

**风格约束**：现有工具函数（如 `collect_preferences(user_input: str, current_preferences: dict | None)`）
都是分开的类型化参数，不是单个 dict 参数。新工具函数必须保持同样风格，否则 LangChain 的
`@tool` 装饰器做 schema 推断时体验不一致。

```python
@tool
async def classify_intent(
    user_input: str,
    has_existing_itinerary: bool,
    needs_clarification: bool,
) -> dict:
    """调用 LLM 做意图分类，用 config.py 里已配置的 openai_base_url/openai_model
    （即项目现有的 DeepSeek 接入方式，复用 memory/long_term.py 里 openai.OpenAI 的
    初始化模式）。LLM 调用失败/超时（建议 timeout=8s）时返回
    {"intent": "new_plan", "confidence": 0.0, "fallback": True}，
    由调用方（intent_router 节点）决定是否再走启发式规则。"""

@tool
async def answer_itinerary_question(question: str, itinerary: str, weather_summary: str, budget_summary: str) -> str:
    """基于已有行程回答用户问题"""

@tool
async def generate_chitchat_reply(message: str) -> str:
    """生成闲聊回复，控制在1-2句话，可引导用户使用规划功能"""
```

### 5. `agent/travel_agent.py`

**5.1 `__init__` 改签名**：
```diff
  def __init__(
      self,
+     graph: CompiledStateGraph,   # 由外部（main.py lifespan）传入，不再内部 import travel_graph
      llm_client: Any | None = None,
      memory_manager: Any | None = None,
      ...
  ):
-     self.graph = travel_graph
+     self.graph = graph
```

**5.2 重写 `plan_travel` 核心执行部分**（保留 SSE 事件契约，前端不用改）：

关键点：用 `self.graph.astream(state, config={"configurable": {"thread_id": thread_id}}, stream_mode="updates")`
逐节点消费执行结果，每收到一个节点的输出就 `yield` 一次 `progress` 事件（复用现有
`node_messages` 映射表），节点名和状态字段的判断逻辑（`needs_clarification` 触发 `clarify` 事件、
最终 `itinerary` 触发 `complete` 事件）基本照搬现有 `plan_travel` 里已经写好的判断代码，
只是触发时机从"手动 for 循环里"换成"astream 每次 yield 出一个节点结果时"。

`thread_id` 直接用 `session_id`（不需要像草案里搞一个独立的 thread_id 概念，
一个会话就是一条 LangGraph 线程，简化状态映射）。

**5.3 `chat()` 方法**：评估后建议直接删除，合并进 `plan_travel`。因为有了 `intent_router`，
"追问 vs 问答 vs 闲聊 vs 新规划"的判断已经在图内部用 LLM 做了，不需要在 `TravelAgent` 层
再维护一套 `chat()` 的独立分支逻辑。`main.py` 里调用 `agent.chat(...)` 的地方（`/api/chat/stream`
端点）改成也调用 `plan_travel`。**这是本方案里改动面最大、风险最高的一步**，需要你评阅时重点看。

### 6. `main.py`

**6.1 `lifespan` 改造**：
```python
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from agent.graph import build_travel_graph

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[startup] begin", flush=True)
    # ... 现有 tunnel_manager 逻辑不变 ...
    # ... 现有 memory_manager 初始化不变 ...

    pg_conn_str = settings.session_history_db_url.replace("postgresql+psycopg2://", "postgresql://")
    print("[startup] initializing LangGraph checkpointer", flush=True)
    async with AsyncPostgresSaver.from_conn_string(pg_conn_str) as checkpointer:
        await checkpointer.setup()
        graph = build_travel_graph(checkpointer=checkpointer)
        app.state.agent = TravelAgent(graph=graph, memory_manager=memory_manager)
        print("[startup] agent ready (with checkpointer)", flush=True)
        app.state.start_time = asyncio.get_event_loop().time()

        yield   # yield 必须在 async with 内部，否则 checkpointer 连接在请求处理期间被关掉

        # 关闭
        if hasattr(app.state, "agent"):
            del app.state.agent
    # async with 退出时 checkpointer 自动关闭连接
```

**注意**：`settings.session_history_db_url` 现在的值是 `postgresql+psycopg2://...`（今天早些
时候为了修 SQLAlchemy 的 bug 改过），给 `AsyncPostgresSaver.from_conn_string` 用之前要去掉
`+psycopg2` 标记，因为 psycopg v3 的连接字符串不认这个 SQLAlchemy 专用前缀。

**风险**：`yield` 现在被包在 `async with` 内部，如果 FastAPI 请求处理期间抛未捕获异常，
`async with` 的退出流程需要确认不会提前关闭 checkpointer 连接（这是 asynccontextmanager 嵌套的
已知细节，需要在实施阶段写一个「断开重连不影响正在处理的请求」的手动测试用例）。

## 五、验收清单

1. **基础断点续传**：发消息触发规划，中途系统追问缺失字段时，**手动重启后端进程**，
   用同一个 `session_id` 继续回答，验证能否从追问处继续，而不是从头重新问一遍
2. **意图路由准确率**：至少测试以下 4 类输入，确认路由到正确分支：
   - "去上海玩3天预算1000"（应命中 new_plan）
   - 系统追问"预算多少"后回答"3000"（应命中 continue_clarify）
   - 已生成行程后问"第二天几点出发"（应命中 faq_about_itinerary）
   - "你好"、"你是谁"（应命中 chitchat）
3. **现有功能不退化**：确认 `should_clarify`、`safety_check` 两个条件边和 9 个既有节点
   在新的图结构下依然正确执行，行程质量跟今天已经修复过的版本（去重/中文化/表格/时间不重叠/
   动态数据来源）保持一致
4. **SSE 事件格式不变**：前端 `TravelContext.tsx` 的 `handleEvent` 不需要改动，
   status/progress/clarify/reply/complete/error 六种事件类型的 payload 结构跟改造前一致

## 五点五、Windows 特有坑（验证脚本阶段发现）

`psycopg` 的异步模式（`AsyncPostgresSaver` 依赖）在 Windows 上不兼容默认的
`ProactorEventLoop`，报错：
```
psycopg.InterfaceError: Psycopg cannot use the 'ProactorEventLoop' to run in async mode.
```
修复：在程序入口（`verify_checkpointer.py` 和后续 `main.py`）设置事件循环策略：
```python
import asyncio, sys
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```
必须在 `asyncio.run(...)` 或 uvicorn 启动之前设置。`main.py` 目前用
`uvicorn.run("main:app", ...)` 启动（main.py 文件末尾），需要在这一行之前加上述设置。

## 六、待你评阅的关键决策点

1. **5.3 是否删除 `chat()` 方法，合并进 `plan_travel`** —— 这是改动面最大的一步，
   如果你觉得风险太高，可以保留 `chat()` 但让它内部也走 `intent_router`，风险更低但会有
   两套代码路径共享同一套节点逻辑，需要更仔细的状态同步。
2. **thread_id 是否等于 session_id** —— 方案里简化成一一对应，如果你后续想让同一个用户
   在多个"话题"之间切换（比如先规划上海行程，又开一个新的北京规划，但还想留着上海那条
   继续问），可能需要 thread_id 和 session_id 分离，现在提前问清楚比后面重构省事。
3. **`langgraph-checkpoint-postgres` 版本锁定 3.1.0** —— 目前只在你本地验证过这个版本，
   还没有实际跑通一次完整的 setup() + checkpoint 写入/恢复流程，建议实施第一步就是
   写一个独立的最小验证脚本（不接入主流程），确认 checkpoint 真的能在重启后恢复状态，
   再往主代码里接。
