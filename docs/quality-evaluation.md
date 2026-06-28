# 面试质量评测基线

`backend/app/quality/interview_quality.py` 对已完成的 Interview Round 做确定性检查，作为修改 Prompt、模型或面试编排后的最低回归门槛。

当前指标：

- `round_integrity`：每轮是否同时包含问题、回答和持久化评估。
- `evaluation_completeness`：逐轮评估字段是否齐全。
- `question_repetition_rate`：基于字符三元组的近似重复率，门槛为不高于 15%。
- `topic_coverage`：本次面试覆盖的话题数量。
- `score_variance`：逐轮得分是否具有区分度，暂时只记录、不设硬门槛。

运行 `pytest tests/test_interview_quality.py` 可验证指标实现。下一阶段可在固定简历、JD 与题库上导出真实模型结果，将结果 JSON 交给同一 Module，从而比较模型和 Prompt 版本。
