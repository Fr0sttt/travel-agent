# Travel Agent 项目执行计划

## 项目概述
构建一个可解释的旅行规划Agent，包含工具调用、Langfuse观测评估、多维度评估体系、记忆管理、上下文工程和安全防护的完整可交互Web应用。

## 技术栈
- **前端**: React + TypeScript + Tailwind CSS + shadcn/ui
- **后端**: Python FastAPI
- **Agent框架**: LangGraph + OpenAI Agents SDK
- **观测**: Langfuse
- **记忆**: mem0 + 类MemGPT上下文管理
- **数据源**: OpenTripMap, Nominatim, OSRM, Open-Meteo
- **评估**: 借鉴4篇论文的评估框架

## 阶段划分

### Stage 1: 架构设计与文档编写
- 编写完整的技术实现方案文档 (travel_agent_design.md)
- 设计数据库schema和API接口
- 设计评估指标体系
- 设计记忆管理架构
- 设计安全防护机制
- **技能**: report-writing

### Stage 2: 后端Agent核心开发 (并行)
- **子任务2a**: Agent核心引擎 + 工具调用模块
  - 偏好收集器 (collect_preferences)
  - POI搜索 (search_places) - OpenTripMap
  - 地理编码 (geocode_location) - Nominatim
  - 路线估算 (estimate_route) - OSRM
  - 天气查询 (get_weather) - Open-Meteo
  - 预算估算 (estimate_budget)
  - Langfuse集成
  
- **子任务2b**: 记忆管理系统
  - 短期记忆管理 (对话上下文)
  - 长期记忆管理 (向量数据库 + RAG)
  - mem0集成
  - 上下文压缩与修剪
  
- **子任务2c**: 安全防护系统
  - 工具权限分级
  - Prompt Injection防护
  - Secret管理
  - Human-in-the-loop确认机制

### Stage 3: 评估系统开发 (并行)
- **子任务3a**: 端到端评估
  - 借鉴DeepResearch-Bench RACE框架
  - 报告质量评估 (Comprehensiveness, Depth, Instruction-Following, Readability)
  
- **子任务3b**: 推理评估
  - 借鉴DoVer框架
  - 干预驱动调试
  - Trial Success Rate, Progress Made指标
  
- **子任务3c**: 工具调用评估
  - 借鉴Agent-World框架
  - 工具使用正确性、参数准确性
  - 多步工具链评估
  
- **子任务3d**: RAG评估
  - 借鉴FACT框架
  - Citation Accuracy, Effective Citations
  - 检索相关性评估

### Stage 4: 测试数据集构建
- 20+评估测试用例
- 覆盖常规规划、预算约束、偏好约束、变化处理、安全边界
- 多语言支持

### Stage 5: Web应用开发
- **前端**: React + TypeScript + Tailwind + shadcn/ui
- **后端API**: FastAPI
- **交互界面**: 聊天界面 + 行程展示 + 地图集成
- **技能**: vibecoding-webapp-swarm

### Stage 6: 集成测试与部署
- 端到端测试
- Langfuse观测验证
- 安全测试
- 部署为可交互Web应用

## 文件结构
```
travel-agent/
├── docs/
│   └── travel_agent_design.md          # 完整技术实现方案
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                      # FastAPI入口
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── travel_agent.py          # Agent核心
│   │   │   ├── graph.py                 # LangGraph状态机
│   │   │   ├── tools.py                 # 工具定义
│   │   │   └── prompts.py               # 提示词模板
│   │   ├── memory/
│   │   │   ├── __init__.py
│   │   │   ├── short_term.py            # 短期记忆
│   │   │   ├── long_term.py             # 长期记忆
│   │   │   ├── context_manager.py       # 上下文管理
│   │   │   └── mem0_adapter.py          # mem0适配器
│   │   ├── security/
│   │   │   ├── __init__.py
│   │   │   ├── guard.py                 # 安全守卫
│   │   │   ├── permissions.py           # 权限分级
│   │   │   └── sanitizers.py            # 数据清洗
│   │   ├── evaluation/
│   │   │   ├── __init__.py
│   │   │   ├── end_to_end.py            # 端到端评估
│   │   │   ├── reasoning_eval.py        # 推理评估
│   │   │   ├── tool_eval.py             # 工具调用评估
│   │   │   ├── rag_eval.py              # RAG评估
│   │   │   ├── race_framework.py        # RACE框架
│   │   │   ├── fact_framework.py        # FACT框架
│   │   │   └── dover_framework.py       # DoVer框架
│   │   ├── models/
│   │   │   └── schemas.py               # Pydantic模型
│   │   └── config.py                    # 配置
│   ├── tests/
│   │   ├── test_data/
│   │   │   └── eval_cases.json          # 测试数据集
│   │   ├── test_agent.py
│   │   ├── test_tools.py
│   │   ├── test_memory.py
│   │   ├── test_security.py
│   │   └── test_evaluation.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── README.md
```

## 交付物
1. 完整技术实现方案文档
2. 可运行的Travel Agent后端
3. 可交互的Web前端
4. 完整的评估系统
5. 20+测试用例数据集
6. Langfuse集成配置
7. Docker部署配置
