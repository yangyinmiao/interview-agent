from typing import TypedDict, Optional,Annotated, Sequence
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


class InterviewState(TypedDict):
    # === Input ===
    tenant_id: str
    interview_id: str
    resume_id: str
    jd_id: str
    question_bank_id: str
    interview_mode: str  # 'basic' | 'deep' | 'follow_up' | 'stress'
    max_rounds: int

    # === Agent outputs ===
    resume_analysis: Optional[dict]
    jd_analysis: Optional[dict]
    retrieved_questions: Optional[list]

    # === Interview state ===
    current_question: Optional[str]
    current_answer: Optional[str]
    question_history: list[dict]
    follow_up_depth: int
    round_count: int

    # === Evaluation ===
    answer_evaluations: list[dict]
    final_report: Optional[dict]

    # === Messages (for LangGraph message state) ===
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # === Routing ===
    next_action: str  # 'prepare' | 'ask' | 'wait' | 'evaluate' | 'end'


class DocumentState(TypedDict):
    tenant_id: str
    source_type: str  # 'resume' | 'jd' | 'question_bank'
    source_id: str
    file_bytes: Optional[bytes]
    filename: str
    raw_text: Optional[str]
    chunks: Optional[list[dict]]
    status: str  # 'uploaded' | 'parsed' | 'chunked' | 'saved' | 'embedding' | 'completed' | 'failed'
