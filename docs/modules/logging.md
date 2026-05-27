# 日志模块设计

## 1. 概述

结构化日志模块，使用 `contextvars` 实现 async-safe 的全链路元数据追踪，输出 JSON 格式，便于日志聚合和问题排查。

## 2. 设计目标

- **全链路追踪**: 每个日志条目自动携带 `request_id`、`tenant_id`、`interview_id`、`agent` 等上下文
- **Async安全**: 使用 `contextvars` 而非 `threading.local`，确保在 FastAPI async 环境下上下文不丢失
- **结构化输出**: JSON Lines 格式，便于 ELK / Loki / Datadog 等日志平台解析
- **低侵入**: 通过中间件和 Dependency 自动注入，业务代码只需 `logger.info(msg, **extras)`

## 3. 核心架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        Request Pipeline                         │
│                                                                 │
│  Request → RequestLoggingMiddleware → TenantDep → RouteHandler │
│              │                        │                         │
│              ▼                        ▼                         │
│         set_request_id()        set_tenant_id()                 │
│              │                        │                         │
│              └────────┬───────────────┘                         │
│                       ▼                                         │
│              contextvars (async-safe)                           │
│                       │                                         │
│                       ▼                                         │
│              JsonFormatter.format()                             │
│              自动注入 request_id, tenant_id, ...                 │
└─────────────────────────────────────────────────────────────────┘
```

## 4. Context Variables

| 变量 | 类型 | 设置时机 | 作用域 |
|------|------|----------|--------|
| `tenant_id` | `str` | `get_current_tenant` 依赖注入后 | 整个请求 + 下游调用 |
| `request_id` | `str` | `RequestLoggingMiddleware` 入口 | 整个请求生命周期 |
| `interview_id` | `str` | `prepare_context` node 执行时 | 面试流程范围内 |
| `agent_name` | `str` | Agent 内部可选设置 | Agent 执行期间 |

## 5. 日志格式

```json
{
    "timestamp": "2026-05-27T10:30:00.123456+00:00",
    "level": "INFO",
    "logger": "graphs.interview",
    "message": "Preparing interview context",
    "module": "interview_graph",
    "function": "prepare_context_node",
    "line": 42,
    "request_id": "a1b2c3d4-...",
    "tenant_id": "e5f6a7b8-...",
    "interview_id": "c9d0e1f2-...",
    "agent": null,
    "extras": {
        "has_resume": true,
        "has_jd": true,
        "mode": "deep"
    }
}
```

**字段说明**:
- `timestamp`: ISO 8601 UTC 时间戳
- `level`: DEBUG / INFO / WARNING / ERROR
- `message`: 人类可读的日志消息
- `request_id`: 唯一请求ID，贯穿整个请求
- `tenant_id`: 租户ID，认证后自动注入
- `interview_id`: 面试会话ID，面试流程中注入
- `agent`: 当前执行的 Agent 名称
- `extras`: 任意附加的结构化数据
- `exception`: 异常信息（仅在 ERROR 级别 + exc_info 时出现）

## 6. 日志级别使用规范

| 级别 | 使用场景 | 示例 |
|------|----------|------|
| `DEBUG` | 详细的调试信息 | Agent 工具调用详情、Prompt 内容片段 |
| `INFO` | 关键业务节点 | 请求进入/退出、面试轮次、Embedding 完成 |
| `WARNING` | 可恢复的异常 | JSON 解析失败降级、Token 即将过期 |
| `ERROR` | 不可恢复的错误 | LLM 调用失败、数据库连接异常 |

## 7. 关键日志埋点

### 7.1 请求层 (middleware/logging.py)

```
每个 HTTP 请求:
  - INFO: 请求进入 (method, path, query, client)
  - INFO: 请求完成 (status, duration_ms)
  - ERROR: 请求异常 (error_type, error_message)
```

### 7.2 面试流程 (graphs/interview_graph.py)

```
面试生命周期:
  - INFO: 上下文准备开始 (has_resume, has_jd, mode)
  - INFO: 上下文准备完成 (duration_ms, questions_retrieved)
  - INFO: 每轮问题生成 (round_count, question_length)
  - INFO: 每轮答案评估 (score, should_follow_up)
  - DEBUG: 路由决策 (decision, mode)
  - INFO: 面试结束 (total_rounds, overall_score)
```

### 7.3 Embedding管道 (services/embedding_pipeline.py)

```
文档处理:
  - INFO: Chunks 保存到 PG (chunk_count, source_type)
  - INFO: Celery 任务触发 (source_type, source_id)
  - INFO: Embedding 处理开始/完成 (total_chunks, duration_ms)
```

### 7.4 Agent 层 (agents/*.py)

```
InterviewerAgent:
  - INFO: 生成问题 (mode, round_count, topics_covered)
  - WARNING: JSON 解析失败

EvaluatorAgent:
  - DEBUG: 单题评估完成 (score)
  - INFO: 综合报告生成 (overall_score)
  - ERROR: 报告 JSON 解析失败
```

## 8. 使用示例

```python
from app.core.logging import get_structured_logger, LogContext

logger = get_structured_logger("my.module")

# 基本使用
logger.info("Processing started", item_count=10)

# 带异常
try:
    ...
except Exception as e:
    logger.exception("Processing failed", item_id=item_id)

# Context Manager 注入额外上下文
with LogContext(interview_id="xxx", agent_name="resume"):
    logger.info("Analyzing resume")  # 自动携带 interview_id + agent_name

# 在 API 路由中，tenant_id 和 request_id 已由中间件自动注入
@router.post("/interviews")
async def create_interview(tenant=Depends(get_current_tenant)):
    logger.info("Interview created", mode=data.mode)
```

## 9. 运维集成

### 本地开发
```bash
# 输出到 stdout，人类可读模式（调整 JsonFormatter 或使用 | jq）
docker compose logs -f backend | jq
```

### 生产环境
- **ELK Stack**: Filebeat → Logstash → Elasticsearch → Kibana
- **Loki + Grafana**: promtail 收集 → Grafana 查询
- **Datadog**: Agent 自动采集 stdout JSON

### 常用查询
```
# 按 request_id 追踪完整请求链路
request_id:"a1b2c3d4-..."

# 按 tenant_id 查看某租户的所有操作
tenant_id:"e5f6a7b8-..."

# 按 interview_id 查看面试全过程
interview_id:"c9d0e1f2-..."

# 查看所有 ERROR 日志
level:"ERROR"

# 查看某次面试的评分
logger:"graphs.interview" AND message:"Interview completed"
```

## 10. 文件清单

| 文件 | 说明 |
|------|------|
| `backend/app/core/logging.py` | 核心日志模块 (Formatter, ContextVar, Logger工厂) |
| `backend/app/middleware/logging.py` | 请求日志中间件 (RequestLoggingMiddleware) |
| `backend/app/core/tenant.py` | 租户依赖注入 (set_tenant_id) |
| `backend/app/main.py` | 应用启动 (中间件注册, 启动日志) |
| `backend/app/graphs/interview_graph.py` | 面试流程关键埋点 |
| `backend/app/agents/interviewer_agent.py` | 面试官Agent日志 |
| `backend/app/agents/evaluator_agent.py` | 评估Agent日志 |
| `backend/app/services/embedding_pipeline.py` | Embedding管道日志 |
| `backend/app/tasks/embedding_tasks.py` | Celery任务日志 |
