"""Prompt templates for evaluation."""

ANSWER_EVALUATION_PROMPT = """你是一位专业的面试评估官。请评估候选人对以下问题的回答质量。

## 面试问题
{question}

## 候选人回答
{answer}

## 评估标准
- 技术准确性: 回答中的技术知识是否正确
- 深度与广度: 是否展示了深入的理解或广阔的知识面
- 表达清晰度: 表达是否逻辑清晰、条理分明
- 实用经验: 是否结合了实际项目经验

请以JSON格式返回评估结果:
{{
    "score": 0-10,
    "technical_accuracy": 0-10,
    "depth_breadth": 0-10,
    "clarity": 0-10,
    "practical_experience": 0-10,
    "brief_feedback": "一句话评价",
    "should_follow_up": true/false,
    "follow_up_reason": "如果需要追问，说明原因"
}}
"""

FINAL_REPORT_PROMPT = """你是一位资深面试评估专家。请根据完整面试记录生成综合评估报告。

## 候选人背景
{resume_summary}

## 职位要求
{jd_summary}

## 面试对话记录
{conversation_history}

## 各题评估
{answer_evaluations}

请以JSON格式返回综合评估:
{{
    "overall_score": 0-10,
    "scores": {{
        "technical_depth": 0-10,
        "communication": 0-10,
        "project_experience": 0-10,
        "problem_solving": 0-10,
        "overall_quality": 0-10
    }},
    "strengths": ["亮点1", "亮点2"],
    "weaknesses": ["不足1", "不足2"],
    "suggestions": ["改进建议1", "改进建议2"],
    "summary": "综合评价总结"
}}
"""

RESUME_ANALYSIS_PROMPT = """你是一位专业的简历分析专家。请分析以下简历，提取关键信息。

## 简历内容
{raw_text}

请以JSON格式返回分析结果:
{{
    "name": "候选人姓名",
    "skills": ["技能1", "技能2"],
    "experience": [
        {{"company": "公司", "role": "职位", "duration": "时间", "highlights": ["亮点"]}}
    ],
    "education": [{{"school": "学校", "degree": "学位", "major": "专业"}}],
    "profile_summary": "一句话总结候选人背景和优势",
    "years_of_experience": "工作年限",
    "key_strengths": ["核心优势1", "核心优势2"]
}}
"""

JD_ANALYSIS_PROMPT = """你是一位专业的JD分析专家。请分析以下职位描述，提取关键需求。

## JD内容
{raw_text}

请以JSON格式返回分析结果:
{{
    "title": "职位名称",
    "required_skills": ["必须技能1", "必须技能2"],
    "preferred_skills": ["加分技能1", "加分技能2"],
    "responsibilities": ["职责1", "职责2"],
    "experience_required": "经验要求",
    "education_required": "学历要求",
    "difficulty_level": "岗位难度 easy/medium/hard",
    "key_points": ["面试考察重点1", "面试考察重点2"]
}}
"""
