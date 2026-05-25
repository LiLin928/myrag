# MyRAG

> 基于 LangChain 1.x + LangGraph 1.x 的 RAG + Agent 工作流平台，Dify 替代方案

## 项目架构

.venv/Scripts/activate

 uv run arq app.tasks.WorkerSettings 

 uv run  -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
myrag-app/
├── backend/                 # Python FastAPI 后端
│   ├── app/
│   │   ├── api/             # API 路由层 (auth, users, documents, workflows, agents...)
│   │   ├── models/          # SQLAlchemy 数据模型 (user, role, document, conversation...)
│   │   ├── services/        # 业务逻辑服务层
│   │   ├── graphs/          # LangGraph 状态机
│   │   │   ├── agent_graph.py      # Agent 对话状态图
│   │   │   ├── workflow_graph.py   # 工作流状态图
│   │   │   └── checkpointer.py     # PostgresSaver 检查点持久化
│   │   ├── workflow/        # 工作流引擎
│   │   │   ├── engine/      # WorkflowEngine (动态构建 StateGraph)
│   │   │   ├── nodes/       # 节点定义 (LLM, RAG, Code, HTTP, Condition, Human, Loop...)
│   │   │   ├── models/      # 工作流模型定义
│   │   │   └── sandbox/     # Docker 代码沙盒池
│   │   ├── rag/             # RAG 模块
│   │   │   ├── extractor/   # 文档提取器 (Text, MinerU, Unstructured)
│   │   │   ├── splitter/    # 文本分割器 (ClauseSplitter)
│   │   │   ├── embedding/   # 向量嵌入服务 (OpenAI 兼容接口)
│   │   │   └── retrieval/   # 检索器 (PgVector, Hybrid)
│   │   ├── tools/           # Agent 工具注册 (HTTP Request, Code Execution, Knowledge Search...)
│   │   ├── tasks/           # ARQ 异步任务 (文档处理、进度追踪)
│   │   ├── core/            # 核心组件 (安全认证、数据库初始化)
│   │   ├── middleware/      # 中间件 (WebSocket 进度推送)
│   │   └── db/              # 数据库扩展 (Vector Extension)
│   ├── pyproject.toml       # 项目依赖配置
│   └── .venv/               # Python 虚拟环境
│
├── frontend/                # React 前端
│   ├── React 18 + Vite + TypeScript
│   ├── Ant Design 5 (UI 组件库)
│   ├── ReactFlow (工作流可视化编辑器)
│   ├── Monaco Editor (代码/技能编辑)
│   ├── Socket.io-client (实时通信)
│   └── Zustand (状态管理)
│
└── docker/                  # Docker Compose 配置
    ├── PostgreSQL + PGVector
    ├── Redis
    └── MinIO
```

## 技术栈

### 后端

| 类别 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI + Uvicorn | 0.136.1 / 0.46.0 |
| 数据库 | PostgreSQL + asyncpg + SQLAlchemy | 2.0.49 |
| 向量存储 | pgvector | 0.4.2 |
| 任务队列 | Redis + ARQ | 5.3.1 / 0.28.0 |
| 文件存储 | MinIO | 7.2.20 |
| **LangChain** | langchain | **1.2.18** |
| **LangChain Core** | langchain-core | **1.4.0** |
| **LangChain Anthropic** | langchain-anthropic | **1.4.3** |
| **LangChain OpenAI** | langchain-openai | **1.2.1** |
| **LangChain Community** | langchain-community | **0.4.1** |
| **LangGraph** | langgraph | **1.1.10** |
| **LangGraph Checkpoint** | langgraph-checkpoint-postgres | **3.1.0** |
| Embedding | OpenAI API (兼容接口) | text-embedding-3-small |
| 代码沙盒 | Docker SDK | 7.1.0 |
| 安全认证 | python-jose + passlib + bcrypt | - |

### 前端

| 类别 | 技术 | 版本 |
|------|------|------|
| 框架 | React + Vite + TypeScript | 18.2 / 5.0 / 5.3 |
| UI 组件 | Ant Design | 5.12.0 |
| 工作流编辑 | ReactFlow | 11.10.0 |
| 代码编辑 | Monaco Editor | 4.6.0 |
| 实时通信 | Socket.io-client | 4.7.0 |
| 状态管理 | Zustand | 4.5.0 |

## 核心模块

### LangGraph 状态机

项目使用 LangGraph 实现两个核心状态机：

1. **Agent 对话图** (`app/graphs/agent_graph.py`)
   - 多轮对话状态管理
   - 工具调用 → 思考 → 响应循环
   - 人工介入节点 (`interrupt_before`)
   - PostgresSaver 检查点持久化

2. **工作流引擎** (`app/workflow/engine/workflow_engine.py`)
   - 基于节点定义动态构建 StateGraph
   - 支持节点类型：LLM、RAG、Code、HTTP、Condition、Human、Loop、Tool
   - 中断恢复机制

### RAG 模块

- **文档提取**: 支持 Text、MinerU、Unstructured 多种提取器
- **文本分割**: ClauseSplitter 智能分句
- **向量嵌入**: OpenAI 兼容接口，支持缓存和批量处理
- **检索**: PgVector 检索 + Hybrid 混合检索

## 快速开始

### 1. 启动基础设施

```bash
cd docker
docker-compose up -d
```

### 2. 启动后端 API 服务

```bash
cd backend
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

### 3. 启动后台任务 Worker (文档解析、向量化等)

```bash
cd backend
arq app.tasks.WorkerSettings
```

> **注意**: 后台任务（如文档解析、向量化）需要启动 ARQ Worker 才能执行。如果不启动 Worker，点击"解析"按钮后任务只会加入队列，不会真正执行。

### 4. 启动前端

```bash
cd frontend
npm install
npm run dev
```
