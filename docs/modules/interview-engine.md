# 面试引擎设计

## 1. 概述

面试引擎是系统的核心模块，基于 LangGraph StateGraph 实现，驱动完整的面试流程。

当前实现中，LangGraph 负责首次资料准备和首问生成；之后每个 Interview Round 由 `app/interview/session.py` 统一完成。这样 JSON 与 SSE Adapter 不再各自维护一套轮次、评估和报告状态。

## 2. LangGraph 面试流程

### 2.1 状态机图

```
START
  │
  ▼
[prepare_context] ── 并行调用 ResumeAgent + JDAgent + QBankAgent
  │
  ▼
[generate_question] ── InterviewerAgent 根据模式生成问题
  │
  ▼
  [FastAPI 返回问题给前端，等待用户输入]
  │
  ▼
[evaluate_answer] ── EvaluatorAgent 评估回答质量
  │
  ├── router: "ask" ──→ [generate_question] (循环)
  │
  └── router: "end" ──→ [generate_report] ──→ END
```

### 2.2 核心代码结构

**文件**: `backend/app/graphs/interview_graph.py`

```python
def build_interview_graph(db: AsyncSession) -> CompiledStateGraph:
    workflow = StateGraph(InterviewState)

    workflow.add_node("prepare_context", prepare_context_node)
    workflow.add_node("generate_question", generate_question_node)
    workflow.add_node("evaluate_answer", evaluate_answer_node)
    workflow.add_node("generate_report", generate_report_node)

    workflow.set_entry_point("prepare_context")
    workflow.add_edge("prepare_context", "generate_question")
    workflow.add_edge("generate_question", "evaluate_answer")

    workflow.add_conditional_edges(
        "evaluate_answer",
        router_function,           # 返回 'ask' | 'end'
        {"ask": "generate_question", "end": "generate_report"}
    )

    workflow.add_edge("generate_report", END)
    return workflow.compile()
```

### 2.3 关键节点说明

#### prepare_context_node — 上下文准备

并行执行三个 Agent，构建面试所需的完整上下文：
```python
resume_result, jd_result, qbank_result = await asyncio.gather(
    resume_agent.run(resume_id, tenant_id),
    jd_agent.run(jd_id, tenant_id),
    qbank_agent.search(question_bank_id, tenant_id, context=jd_context),
)
```

#### generate_question_node — 生成问题

InterviewerAgent 根据模式和上下文生成下一个面试问题。支持以下模式：

| 模式 | Prompt 策略 |
|------|------------|
| `basic` | 标准面试，从简历/JD/题库中选题，友好专业 |
| `deep` | 深挖技术细节，追问实现原理和设计决策 |
| `follow_up` | 递进追问链：是什么 → 为什么 → 怎么优化 |
| `stress` | 质疑每个回答，设置高压场景 |

#### evaluate_answer_node — 评估回答

EvaluatorAgent 对单个回答按多个维度评分，结果存入 State。

#### generate_report_node — 生成报告

获取全部对话历史，生成综合评估报告（评分 + 亮点 + 不足 + 建议）。

### 2.4 路由逻辑 (Supervisor)

```python
def router(state: InterviewState) -> str:
    # 1. 达到最大轮次 → 结束
    if round_count >= max_rounds:
        return "end"

    # 2. 追问模式 + 评分低 + 追问深度未达上限 → 继续追问
    if mode == "follow_up" and follow_up_depth < 3 and score < 7:
        follow_up_depth += 1
        return "ask"

    # 3. 压力面 → 持续质疑
    if mode == "stress":
        return "ask"

    # 4. 默认 → 切换新话题
    return "ask"
```

## 3. 面试状态 (InterviewState)

```python
class InterviewState(TypedDict):
    # 输入参数
    tenant_id: str
    interview_id: str
    resume_id: str
    jd_id: str
    question_bank_id: str
    interview_mode: str     # basic | deep | follow_up | stress
    max_rounds: int

    # Agent 产出
    resume_analysis: Optional[dict]
    jd_analysis: Optional[dict]
    retrieved_questions: Optional[list]

    # 面试运行时
    current_question: Optional[str]
    current_answer: Optional[str]
    question_history: list[dict]
    follow_up_depth: int
    round_count: int

    # 评估
    answer_evaluations: list[dict]
    final_report: Optional[dict]

    # 路由
    next_action: str  # prepare | ask | wait | evaluate | end
```

## 4. 面试模式详解

### 4.1 基础模式 (basic)

- 从简历项目经验和JD技能要求出发
- 结合Qdrant检索的参考题库
- 每次一个问题，语气友好
- 覆盖不同话题，避免重复

### 4.2 深入提问 (deep)

- 针对技术栈深挖实现原理
- 追问设计决策（为什么选这个方案？替代方案？）
- 考察架构和系统设计能力
- 根据回答质量决定深挖或换话题

### 4.3 追问模式 (follow_up)

- 递进式追问链（最多3轮）:
  1. 基础层: 确认基本理解
  2. 原理层: 挖掘深层原理
  3. 优化层: 考察工程思维
- 评分低于7分时继续追问
- 追问链结束后切换话题

### 4.4 压力模式 (stress)

- 保持质疑态度
- 追问极端场景和失败处理
- 设置高压对话环境
- 保持专业性，不进行人身攻击

## 5. Prompt 注入策略

每个 interview mode 的 Prompt 模板在 `prompts/interview_modes.py` 中定义。

注入内容优先级:
1. **必注入**: 简历摘要 + JD摘要 + 面试模式规则
2. **条件注入**: RAG检索到的题库（相似度 > 0.7）
3. **可选注入**: 最近5轮对话历史 + 上一轮评估结果 + 当前追问深度

## 6. RAG 检索流程

```
1. 从当前对话上下文提取搜索关键词
2. Qdrant search:
   - collection: "questions"
   - filter: tenant_id + (可选) tags + (可选) difficulty
   - top_k: 5
   - score_threshold: 0.7
3. 检索结果注入 Prompt
4. 如果无匹配 → 完全基于简历+JD即兴出题
```

## 7. 与 API 的集成

路由层 (`api/v1/interviews.py`) 负责:
1. 创建 Interview 记录 (PG)
2. 首次启动时调用 `graph.ainvoke(initial_state)` 准备资料并生成首问
3. 每次 `generate_question` 后将问题存为 InterviewMessage
4. 每次 `respond` 通过 InterviewSession 完成评分、持久化、路由和下一问生成
5. 面试结束时将 report 存入 InterviewReport

关键交互模式：
- `/start` → `graph.ainvoke()` with `next_action='prepare'`
- `/respond` 与 `/respond-stream` → 同一个 InterviewSession Interface
- 每个候选人消息保存本轮完整 Answer Evaluation，报告从全部持久化评估生成
