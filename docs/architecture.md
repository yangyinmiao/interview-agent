# 模拟面试Agent — 整体架构设计

## 1. 项目概述

构建一个多租户的AI模拟面试平台，支持自定义题库、简历/JD分析、多种面试模式。

核心能力：
- 上传简历并AI分析候选人画像
- 上传JD并提取岗位需求
- 创建命名题库并上传多份资料构建知识库（支持文件追加）
- 多模式模拟面试（基础、深入提问、追问、压力面）
- 面试后自动评估和报告生成

## 2. 技术栈

| 层级 | 技术 | 版本 |
|------|------|------|
| 后端框架 | FastAPI | 0.115+ |
| Agent框架 | LangGraph | 0.2+ |
| LLM抽象 | LangChain | 0.3+ |
| ORM | SQLAlchemy 2.0 (async) | 2.0+ |
| 数据库 | PostgreSQL 16 | - |
| 向量数据库 | Qdrant | latest |
| 任务队列 | Celery + Redis 7 | 5.4+ |
| 文件存储 | MinIO (S3兼容) | latest |
| 前端 | Next.js 14 (App Router) | 14+ |
| 部署 | Docker Compose | - |

## 3. 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                      Docker Compose                          │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                   │
│  │ Next.js  │  │ FastAPI  │  │ Celery   │                   │
│  │ Frontend │──│ Backend  │──│ Workers  │                   │
│  │ :3000    │  │ :8000    │  │          │                   │
│  └──────────┘  └────┬─────┘  └────┬─────┘                   │
│                     │              │                         │
│          ┌──────────┼──────────────┼──────────┐             │
│          │          │              │          │             │
│     ┌────▼──┐  ┌───▼────┐  ┌─────▼────┐ ┌───▼────┐        │
│     │  PG   │  │ Qdrant │  │  Redis   │ │ MinIO  │        │
│     │ :5432 │  │ :6333  │  │  :6379   │ │ :9000  │        │
│     └───────┘  └────────┘  └──────────┘ └────────┘        │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              LangGraph Agent 层                        │  │
│  │                                                       │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐    │  │
│  │  │ Resume   │  │   JD     │  │  QuestionBank    │    │  │
│  │  │ Agent    │  │  Agent   │  │  Agent           │    │  │
│  │  └────┬─────┘  └────┬─────┘  └────────┬─────────┘    │  │
│  │       └──────────────┼───────────────┘               │  │
│  │                      │                               │  │
│  │           ┌──────────▼──────────┐                    │  │
│  │           │  Supervisor Agent   │                    │  │
│  │           └──────────┬──────────┘                    │  │
│  │       ┌──────────────┼───────────────┐               │  │
│  │  ┌────▼─────┐                 ┌──────▼──────┐        │  │
│  │  │Interviewer│                │  Evaluator  │        │  │
│  │  │  Agent   │                 │   Agent     │        │  │
│  │  └──────────┘                 └─────────────┘        │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

## 4. 核心数据流

### 4.1 文档处理流
```
用户上传文件
  → FastAPI 接收 → 存 MinIO
  → DocumentParser 解析文本
  → Chunker 分块
  → 保存 chunk 到 PG (status=pending)
  → 返回 "上传成功"
  → Celery 异步任务
     → 获取 pending chunks
     → Embedding 模型生成向量
     → 写入 Qdrant
     → 更新 PG status=completed
```

### 4.2 面试流程
```
创建面试 → 开始面试
  → LangGraph prepare_context
    → ResumeAgent + JDAgent + QBankAgent (并行)
  → generate_question (InterviewerAgent 生成首问)
  → 返回问题给前端
  → 用户作答
  → evaluate_answer (EvaluatorAgent 评估)
  → Supervisor 路由决策
    ├── 继续追问 → generate_question (循环)
    ├── 切换话题 → generate_question (循环)
    └── 轮次达标 → generate_report (结束)
```

## 5. 多租户设计

采用**行级隔离**策略，所有数据表包含 `tenant_id` 字段。

- PostgreSQL: 所有查询自动注入 `WHERE tenant_id = ?` 条件
- Qdrant: 通过 payload 中的 `tenant_id` 字段过滤
- MinIO: 文件按 `{tenant_id}/{resource_type}/{filename}` 路径组织

JWT 认证后，从 token 解析 tenant_id，通过 FastAPI Dependency 注入所有请求。

## 6. 关键设计决策

### 6.1 LangGraph 多Agent架构

选择 LangGraph 而非单体 service：
- 每个 Agent 职责单一，独立测试和迭代
- StateGraph 天然支持面试流程的状态管理和条件路由
- 新增 Agent（语音、情感分析等）只需添加节点和边
- Agent 间通过共享 State 协作，不直接耦合

### 6.2 上传快 + 异步Embedding

- 上传时：解析 → 分块 → 存 PG（同步，秒级完成）
- Embedding：Celery 异步任务（可耗时较久）
- 支持 Admin API 手动触发批量 embedding

### 6.3 LangChain 多供应商适配

通过环境变量切换 LLM 和 Embedding 供应商：
- LLM: OpenAI / Anthropic / DeepSeek / 智谱
- Embedding: OpenAI / HuggingFace / 本地模型

## 7. 项目目录

```
interview-agent/
├── docs/                    # 设计文档
├── backend/                 # Python FastAPI 后端
│   └── app/
│       ├── agents/          # LangGraph Agent
│       ├── graphs/          # LangGraph StateGraph
│       ├── api/v1/          # REST API 路由
│       ├── core/            # 基础设施 (DB, Qdrant, MinIO, JWT)
│       ├── models/          # SQLAlchemy 模型
│       ├── schemas/         # Pydantic 模型
│       ├── services/        # 业务服务
│       ├── prompts/         # Prompt 模板
│       └── tasks/           # Celery 任务
├── frontend/                # Next.js 前端
│   └── src/app/
│       ├── page.tsx                 # 首页（重定向到登录）
│       ├── login/page.tsx           # 登录/注册页
│       ├── dashboard/
│       │   ├── layout.tsx           # Tab 导航（面试中心/简历/岗位/题库）
│       │   ├── page.tsx             # 面试中心（创建面试 + 历史列表）
│       │   ├── resumes/page.tsx     # 简历管理（上传 + 列表 + 删除）
│       │   ├── jds/page.tsx         # 岗位管理（上传 + 列表 + 删除）
│       │   └── question-banks/page.tsx  # 题库管理（创建 + 追加文件 + 删除）
│       └── interview/[id]/page.tsx  # 面试对话页（自动开始 + 对话 + 报告）
├── docker-compose.yml       # 容器编排
└── .env.example             # 环境变量模板
```

## 8. 开发阶段

### Phase 1: MVP
- Docker Compose 基础设施
- 认证 + 多租户
- 简历/JD/题库上传 + embedding
- 基础面试模式 + LangGraph 流程
- Next.js 前端（登录/上传/对话/报告）
- 面试评估报告

### Phase 2: 深化
- 追问/深入/压力面模式
- 简历/JD 结构化分析
- 多维度评估报告
- Admin 管理界面

### Phase 3: 增强
- 语音输入/输出
- 面试回放
- 题库在线编辑
- 多次面试进步追踪
