from app.models.base import Base
from app.models.tenant import Tenant
from app.models.resume import Resume
from app.models.jd import JD
from app.models.question_bank import QuestionBank
from app.models.document_chunk import DocumentChunk
from app.models.interview import Interview
from app.models.interview_message import InterviewMessage
from app.models.interview_report import InterviewReport

__all__ = [
    "Base",
    "Tenant",
    "Resume",
    "JD",
    "QuestionBank",
    "DocumentChunk",
    "Interview",
    "InterviewMessage",
    "InterviewReport",
]
