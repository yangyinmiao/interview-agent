# 可观测性（LangFuse 集成）· 架构设计文档

> 版本：v1.0（初版）| 日期：2026-05-28
> ⚠️ 执行过程中如有技术方案调整，必须同步更新此文档

---

## 一、背景

interview-agent 当前的日志（`get_structured_logger`）只记录了基本信息（节点耗时、评分结果），无法回答以下生产问题：

- "面试官为什么在这个轮次问了这个问题？" → 需要看 LLM 收到的 prompt 和上下文
- "评估为什么打 7 分？" → 需要看 evaluator 的输入输出
- "面试在第 3 轮卡了 30 秒，卡在哪个节点？" → 需要看节点级耗时分布
- "这场面试花了多少钱？" → 需要 token 统计

---

## 二、选型：LangFuse

| 方案 | 定位 | 适配本项目的理由 |
|------|------|:--|
| **LangFuse** | LLM 专用可观测性 | LangChain/LangGraph 原生集成，`@observe()` 一行装饰器追踪节点 |
| OpenTelemetry + Jaeger | 通用分布式追踪 | 看不出 LLM prompt/response 内容，配置重 |
| Sentry | 错误追踪 | 适合崩溃场景，不适合 LLM 调用链分析 |

LangFuse 自部署开源，docker-compose 加两个服务即可。

---

## 三、架构

```
┌─────────────────────────────────────────────────────┐
│                  Docker Compose                      │
│                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
│  │ Next.js  │  │ FastAPI  │  │  LangFuse Server  │  │
│  │ :3000    │  │ :8000    │  │  :3001 (UI)       │  │
│  └──────────┘  └────┬─────┘  └────────┬─────────┘  │
│                     │                 │             │
│                     │ CallbackHandler │             │
│                     │ + @observe()    │             │
│                     ▼                 ▼             │
│              ┌─────────────┐  ┌──────────────────┐  │
│              │  LLM Calls  │  │  LangFuse PG     │  │
│              │  + Graph    │  │  (internal)      │  │
│              │  Nodes      │  └──────────────────┘  │
│              └─────────────┘                        │
└─────────────────────────────────────────────────────┘
```

**追踪层级**：

| 层级 | 追踪方式 | 覆盖内容 |
|------|----------|---------|
| LLM 调用 | LangChain `CallbackHandler` | prompt · response · tokens · latency · model |
| Graph 节点 | `@observe()` 装饰器 | prepare_context · generate_question · evaluate_answer · generate_report |
| 面试会话 | `session_id` 传入 graph config | 按 interview_id 分组，一次面试一条 Trace |

---

## 四、技术实现

### 4.1 Docker 服务

新增两个容器：

```yaml
langfuse-postgres:
  image: postgres:16-alpine
  environment:
    POSTGRES_DB: langfuse
    POSTGRES_USER: langfuse
    POSTGRES_PASSWORD: langfuse

langfuse:
  image: ghcr.io/langfuse/langfuse:latest
  ports:
    - "3001:3000"
  environment:
    DATABASE_URL: postgresql://langfuse:langfuse@langfuse-postgres:5432/langfuse
    NEXTAUTH_SECRET: langfuse-dev-secret
    NEXTAUTH_URL: http://localhost:3001
    SALT: langfuse-dev-salt
    # Initial admin account
    LANGFUSE_INIT_ORG_ID: org_01
    LANGFUSE_INIT_ORG_NAME: "interview-agent"
    LANGFUSE_INIT_PROJECT_ID: proj_01
    LANGFUSE_INIT_PROJECT_NAME: "production"
    LANGFUSE_INIT_USER_EMAIL: admin@local.dev
    LANGFUSE_INIT_USER_NAME: admin
    LANGFUSE_INIT_USER_PASSWORD: admin123
```

### 4.2 Python 依赖

`requirements.txt` 新增：

```
langfuse==2.60.7
```

> 版本 2.x 的 `langfuse` 包同时包含 LangChain callback 和 `@observe()` 装饰器，无需单独装 `langfuse-langchain`。

### 4.3 配置（config.py）

```python
# LangFuse
langfuse_host: str = "http://localhost:3000"
langfuse_public_key: str = ""
langfuse_secret_key: str = ""
```

初次启动后从 LangFuse UI（`localhost:3001` → Settings → API Keys）获取 key，填入 `.env`。

### 4.4 LLM 工厂（llm_factory.py）

```python
from langfuse.langchain import CallbackHandler

_langfuse_handler: CallbackHandler | None = None

def get_langfuse_handler() -> CallbackHandler:
    global _langfuse_handler
    if _langfuse_handler is None:
        s = get_settings()
        _langfuse_handler = CallbackHandler(
            secret_key=s.langfuse_secret_key,
            public_key=s.langfuse_public_key,
            host=s.langfuse_host,
        )
    return _langfuse_handler

def get_llm() -> BaseChatModel:
    return ChatOpenAI(
        ...,
        callbacks=[get_langfuse_handler()],
    )
```

`get_llm_small()` 同样处理。

### 4.5 Graph 节点（interview_graph.py）

每个节点函数加 `@observe()` 装饰器：

```python
from langfuse import observe

@observe()
async def prepare_context(state): ...

@observe()
async def generate_question(state): ...

@observe()
async def evaluate_answer(state): ...

@observe()
async def generate_report(state): ...
```

### 4.6 面试会话分组（interviews.py）

graph 调用时传入 `session_id`：

```python
result_state = await graph.ainvoke(
    initial_state,
    config={"callbacks": [get_langfuse_handler()], "metadata": {"langfuse_session_id": interview_id}},
)
```

---

## 五、文件变更清单

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `docker-compose.yml` | 新增 | +langfuse-postgres, +langfuse 服务 |
| `backend/requirements.txt` | 新增 | +langfuse==2.60.7 |
| `backend/app/core/config.py` | 新增 | +3 个 langfuse 环境变量 |
| `backend/app/services/llm_factory.py` | 修改 | +get_langfuse_handler()，LLM 注入 callback |
| `backend/app/graphs/interview_graph.py` | 修改 | 节点函数加 @observe() |
| `backend/app/api/v1/interviews.py` | 修改 | graph.ainvoke 传入 session_id |
| `.env`（根目录） | 新增 | +3 个 LANGFUSE_* 变量 |
| `docs/observability-langfuse.md` | 新增 | 本文档 |

---

## 六、使用流程

```bash
# 1. 启动
docker compose up -d

# 2. LangFuse 首次启动较慢（约 30s），等 healthy 后访问
open http://localhost:3001

# 3. 登录：admin@local.dev / admin123
#    进入 Settings → API Keys → Create API Key
#    得到 pk-lf-xxx 和 sk-lf-xxx

# 4. 填入 .env
echo "LANGFUSE_PUBLIC_KEY=pk-lf-xxx" >> .env
echo "LANGFUSE_SECRET_KEY=sk-lf-xxx" >> .env
echo "LANGFUSE_HOST=http://langfuse:3000" >> .env

# 5. 重启 backend
docker compose restart backend

# 6. 进行一次面试 → 打开 LangFuse Traces 页面即可看到完整调用链
```

---

## 七、验收标准

- [ ] `docker compose up -d` 后，`localhost:3001` 可访问 LangFuse UI
- [ ] 进行一次面试后，LangFuse Traces 页面出现完整 Trace
- [ ] Trace 包含：prepare_context → generate_question → ... → generate_report 所有节点
- [ ] 每个节点内可看到 LLM 调用的 prompt、response、tokens、耗时
- [ ] 按 interview_id 能筛选出单次面试的完整 Trace
- [ ] LLM 调用记录中包含 model 名称和 token 消耗
