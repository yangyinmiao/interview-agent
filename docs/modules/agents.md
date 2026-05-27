# Agent 层设计

## 1. 概述

系统采用 LangGraph 多Agent架构，共 6 个 Agent，通过共享 State 协作，由 Supervisor 统一编排。

## 2. Agent 职责矩阵

```
                     ┌─────────────────┐
                     │ Supervisor Agent │  ← 总控，决定下一步调用哪个 Agent
                     └────────┬────────┘
                              │
        ┌──────────┬──────────┼──────────┬──────────┐
        │          │          │          │          │
   ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐
   │ Resume │ │  JD    │ │  QBank │ │  Inter-│ │  Eval- │
   │ Agent  │ │ Agent  │ │  Agent │ │  viewer│ │  uator │
   │        │ │        │ │        │ │  Agent │ │  Agent │
   └────────┘ └────────┘ └────────┘ └────────┘ └────────┘
   解析简历    解析JD     题库检索    面试对话    评估报告
   结构提取    需求提取   题目管理    模式切换    多维评分
   能力画像    匹配分析   RAG检索    追问决策    改进建议
```

## 3. 各Agent详细设计

### 3.1 ResumeAgent

**文件**: `backend/app/agents/resume_agent.py`

**职责**: 解析简历文件，提取结构化信息，生成候选人能力画像。

**工具**:
- `extract_structured_info(raw_text)` — LLM提取技能、经历、教育等结构化数据

**产出**:
```json
{
    "name": "候选人姓名",
    "skills": ["Python", "React", "K8s"],
    "experience": [{"company": "...", "role": "...", "duration": "...", "highlights": [...]}],
    "education": [{"school": "...", "degree": "...", "major": "..."}],
    "profile_summary": "5年后端开发，擅长高并发系统设计...",
    "years_of_experience": "5年",
    "key_strengths": ["核心优势1", "核心优势2"]
}
```

**输入**: `resume_id`, `tenant_id`
**输出**: 结构化分析 dict，同时写回 `resumes.structured` 字段

### 3.2 JDAgent

**文件**: `backend/app/agents/jd_agent.py`

**职责**: 解析JD文件，提取岗位需求，分析技能匹配度。

**工具**:
- `extract_requirements(raw_text)` — LLM提取技能要求、职责、难度等级

**产出**:
```json
{
    "title": "职位名称",
    "required_skills": ["Python", "K8s"],
    "preferred_skills": ["ML经验"],
    "responsibilities": ["职责1", "职责2"],
    "experience_required": "3-5年",
    "education_required": "本科及以上",
    "difficulty_level": "medium",
    "key_points": ["面试考察重点1", "面试考察重点2"]
}
```

**输入**: `jd_id`, `tenant_id`
**输出**: 结构化分析 dict，同时写回 `jds.structured` 字段

### 3.3 QBankAgent

**文件**: `backend/app/agents/qbank_agent.py`

**职责**: 管理题库，提供语义检索能力。

**工具**:
- `search_questions(query, tenant_id, top_k, score_threshold)` — Qdrant语义搜索
- `search_by_topic(topic, tenant_id, top_k)` — 按主题检索

**检索策略**:
1. Qdrant semantic search (cosine similarity)
2. tenant_id 过滤确保多租户隔离
3. score_threshold 默认 0.7，低于阈值时回退到基于简历+JD即兴出题
4. 返回 top_k=5 条最相关问题

### 3.4 InterviewerAgent

**文件**: `backend/app/agents/interviewer_agent.py`

**职责**: 核心面试官，根据模式和上下文生成面试问题，管理对话流程。

**工具**:
- `generate_question(mode, context, history, ...)` — 生成下一个面试问题

**支持模式**:
| 模式 | 策略 | Prompt 文件 |
|------|------|------------|
| `basic` | 基础问答，友好专业 | `prompts/interview_modes.py::BASIC_INTERVIEW_PROMPT` |
| `deep` | 深入技术细节，追问原理 | `prompts/interview_modes.py::DEEP_INTERVIEW_PROMPT` |
| `follow_up` | 2-3轮递进追问链 (是什么→为什么→怎么优化) | `prompts/interview_modes.py::FOLLOW_UP_INTERVIEW_PROMPT` |
| `stress` | 高压质疑，测试抗压能力 | `prompts/interview_modes.py::STRESS_INTERVIEW_PROMPT` |

**Prompt 注入内容**:
- 候选人简历摘要
- JD 职位要求
- RAG 检索到的参考题库
- 当前进度 (轮次/总轮次/追问深度)
- 最近对话历史 (最近5轮)
- 上一轮评估结果 (追问模式)

### 3.5 EvaluatorAgent

**文件**: `backend/app/agents/evaluator_agent.py`

**职责**: 逐题评估回答质量，生成综合面试报告。

**工具**:
- `evaluate_single(question, answer)` — 单题评估，使用小模型降低成本
- `evaluate_overall(resume, jd, history, evaluations)` — 综合评估报告

**评估维度 (单题)**:
- 技术准确性 (0-10)
- 深度与广度 (0-10)
- 表达清晰度 (0-10)
- 实用经验 (0-10)
- 综合评分 (0-10)

**评估维度 (综合报告)**:
- 技术深度 (0-10)
- 沟通表达 (0-10)
- 项目经验 (0-10)
- 问题解决 (0-10)
- 综合素质 (0-10)
- 亮点 / 不足 / 改进建议

**LLM选择策略**:
- 单题评估: 使用小模型 (如 gpt-4o-mini / claude-haiku) 降低成本
- 综合报告: 使用主模型保证质量

### 3.6 SupervisorAgent

**文件**: `backend/app/agents/supervisor.py`

**职责**: 根据当前面试状态做路由决策。

**路由逻辑**:
```
if round_count >= max_rounds → end
if mode == 'follow_up' and follow_up_depth < 3 and score < 7 → 继续追问
if mode == 'stress' → 持续质疑
default → 切换新话题
```

## 4. Agent 间通信

所有 Agent 通过 LangGraph 共享 `InterviewState` 协作：

```python
class InterviewState(TypedDict):
    # 上下文 (ResumeAgent + JDAgent 产出)
    resume_analysis: Optional[dict]
    jd_analysis: Optional[dict]
    retrieved_questions: Optional[list[dict]]  # QBankAgent 产出

    # 面试状态 (InterviewerAgent 产出)
    interview_mode: str
    current_question: Optional[str]
    question_history: list[dict]
    follow_up_depth: int
    round_count: int

    # 评估 (EvaluatorAgent 产出)
    answer_evaluations: list[dict]
    final_report: Optional[dict]

    # 路由
    next_action: str
```

Agent 只读写 State，不直接调用其他 Agent。Supervisor 读取 State 中的 `round_count`、`follow_up_depth`、`answer_evaluations` 等字段做路由决策。

## 5. Agent 基类

**文件**: `backend/app/agents/base.py`

```python
class BaseAgent:
    def __init__(self, llm=None, tools=None):
        self._llm = llm      # 延迟初始化
        self.tools = tools or []

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            self._llm = get_llm()  # 从工厂获取
        return self._llm

    async def invoke_llm(self, prompt: str) -> str:
        ...
```

每个 Agent 继承 BaseAgent，通过 `@tool` 装饰器注册工具函数，使用 `self.llm` 调用大模型。

## 6. 扩展指南

新增 Agent 的步骤：
1. 创建 `agents/new_agent.py`，继承 `BaseAgent`
2. 定义 Agent 的工具函数（`@tool` 装饰器）
3. 在 `graphs/interview_graph.py` 中注册新节点
4. 在 `graphs/states.py` 中添加新 Agent 需要的状态字段
5. 在 Supervisor 的 `router()` 中添加新路由规则
