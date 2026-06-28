# Interview Practice

This context describes the language of an AI-guided practice interview, from preparation material through a completed assessment and progress over time.

## Language

**Practice Interview**:
A bounded interview attempt configured with a mode, preparation material, and a target number of rounds. One Practice Interview contains zero or more Interview Rounds and at most one Interview Report.
_Avoid_: Session, conversation, mock

**Interview Round**:
One interviewer question, one candidate answer, and the resulting Answer Evaluation. A round is complete only after the answer has been evaluated.
_Avoid_: Turn, message pair

**Preparation Material**:
A Resume, Job Description, or Question Bank selected to ground a Practice Interview.
_Avoid_: Context file, attachment

**Answer Evaluation**:
The persisted assessment of one completed Interview Round, including dimension scores, feedback, topic, and whether a follow-up is useful.
_Avoid_: Score, transient evaluation

**Interview Report**:
The aggregate assessment produced from every completed Interview Round in one Practice Interview.
_Avoid_: Final evaluation, summary

**Progress Trend**:
A comparison of completed Interview Reports and Answer Evaluations across multiple Practice Interviews for the same tenant.
_Avoid_: Dashboard statistics, history

## Flagged ambiguities

- “Round count” means completed Interview Rounds, not the number of interviewer messages. A closing message is never a round.
- “History” may refer to message history or completed Practice Interviews; use the specific term in code and documentation.

## Example dialogue

Developer: “When does an Interview Round count toward the target?”

Domain expert: “After the candidate answer has an Answer Evaluation. The next question and the closing message do not increment it.”

Developer: “What feeds the Interview Report?”

Domain expert: “Every persisted Answer Evaluation and its question and answer from that Practice Interview.”
