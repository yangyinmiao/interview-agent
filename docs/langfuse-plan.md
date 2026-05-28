# LangFuse 可观测性集成 · 实现计划

> 关联设计：`docs/observability-langfuse.md`

## 任务列表

| # | 描述 | 状态 | 验收标准 |
|---|------|:--:|----------|
| 1 | docker-compose 新增 langfuse + langfuse-postgres 服务 | 🔲 | `docker compose up -d` 后 localhost:3001 可访问 |
| 2 | requirements.txt 加 langfuse 依赖并重建镜像 | 🔲 | 容器内 `pip list \| grep langfuse` 有输出 |
| 3 | config.py 新增 3 个 LangFuse 环境变量 | 🔲 | Settings 对象可读取 langfuse_host/key |
| 4 | llm_factory.py 新增 get_langfuse_handler()，LLM 注入 callback | 🔲 | `get_llm()` 返回的 LLM 带 callback |
| 5 | interview_graph.py 节点函数加 @observe() 装饰器 | 🔲 | 4 个节点函数均有 @observe() |
| 6 | interviews.py graph.ainvoke 传入 session_id | 🔲 | 3 处 graph.ainvoke 均传入 langfuse config |
| 7 | .env 加 LANGFUSE_* 变量占位 | 🔲 | .env 中有 3 个 LANGFUSE_* 变量 |
| 8 | docker compose 全量重启 + 端到端验证 | 🔲 | LangFuse UI 可访问，Trace 记录正常 |

## 串行/并行说明

- 任务 1-3 无依赖，可并行
- 任务 4 依赖 3（需要读取 config）
- 任务 5 依赖 2（需要 langfuse 包）
- 任务 6 依赖 4（需要 get_langfuse_handler）
- 任务 7 独立
- 任务 8 依赖所有前序任务

建议执行顺序：1 → 2 → 3 → (4, 5, 7 并行) → 6 → 8
