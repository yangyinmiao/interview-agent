# API 设计

## 1. 概述

- 所有 API 以 `/api/v1` 为前缀
- 除认证接口外，均需 JWT Bearer Token
- 租户身份从 JWT 解析，通过 FastAPI Dependency 注入
- 请求/响应使用 JSON，文件上传使用 multipart/form-data

## 2. 认证 (Auth)

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/v1/auth/register` | 否 | 注册新租户 |
| POST | `/api/v1/auth/login` | 否 | 登录，返回 JWT |
| GET | `/api/v1/auth/me` | 是 | 获取当前租户信息 |

**注册请求**:
```json
{
    "name": "张三",
    "email": "zhangsan@example.com",
    "password": "password123"
}
```

**登录响应**:
```json
{
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer"
}
```

## 3. 简历管理 (Resumes)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/resumes/upload` | 上传简历文件 (PDF/DOCX/TXT) |
| GET | `/api/v1/resumes` | 简历列表 |
| GET | `/api/v1/resumes/{id}` | 简历详情（含解析状态） |
| GET | `/api/v1/resumes/{id}/analysis` | 触发 LLM 分析，返回结构化结果 |
| DELETE | `/api/v1/resumes/{id}` | 删除简历 |

**上传响应**:
```json
{
    "id": "uuid",
    "filename": "resume.pdf",
    "parse_status": "parsed",
    "structured": null,
    "created_at": "2026-05-27T10:00:00Z"
}
```

**分析响应**:
```json
{
    "resume_id": "uuid",
    "analysis": {
        "name": "张三",
        "skills": ["Python", "React"],
        "experience": [...],
        "profile_summary": "..."
    },
    "parse_status": "completed"
}
```

## 4. JD管理 (JDs)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/jds/upload` | 上传JD文件 |
| GET | `/api/v1/jds` | JD列表 |
| GET | `/api/v1/jds/{id}` | JD详情 |
| GET | `/api/v1/jds/{id}/analysis` | 触发 LLM 分析 |
| DELETE | `/api/v1/jds/{id}` | 删除JD |

接口结构同简历管理。

## 5. 题库管理 (Question Banks)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/question-banks/upload` | 上传题库文件 |
| GET | `/api/v1/question-banks` | 题库列表 |
| GET | `/api/v1/question-banks/{id}` | 题库详情 |
| DELETE | `/api/v1/question-banks/{id}` | 删除题库 |

## 6. 面试 (Interviews)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/interviews` | 创建面试会话 |
| POST | `/api/v1/interviews/{id}/start` | 开始面试，返回第一个问题 |
| POST | `/api/v1/interviews/{id}/respond` | 候选人作答，返回下一个问题 |
| GET | `/api/v1/interviews/{id}/messages` | 面试对话历史 |
| POST | `/api/v1/interviews/{id}/end` | 手动结束面试 |
| GET | `/api/v1/interviews/{id}/report` | 获取评估报告 |
| GET | `/api/v1/interviews` | 面试历史列表 |

**创建面试请求**:
```json
{
    "resume_id": "uuid (可选)",
    "jd_id": "uuid (可选)",
    "question_bank_id": "uuid (可选)",
    "mode": "basic",
    "max_rounds": 10
}
```

**面试模式枚举**: `basic` | `deep` | `follow_up` | `stress`

**回答请求**:
```json
{
    "answer": "我在项目中使用了React和TypeScript..."
}
```

**回答响应**:
```json
{
    "question": "下一个面试问题...",
    "round_count": 3,
    "max_rounds": 10,
    "status": "active"
}
```

当 `status` 为 `"completed"` 时，面试结束，可获取报告。

**面试对话流程**:
```
POST /interviews          → 创建会话
POST /interviews/{id}/start → 获取首问
POST /interviews/{id}/respond → 作答 + 获取下一问 (循环)
POST /interviews/{id}/end    → 手动结束 (可选)
GET  /interviews/{id}/report → 获取评估报告
```

## 7. 管理 (Admin)

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/admin/trigger-embedding?source_type=resume` | 手动触发 embedding |
| GET | `/api/v1/admin/embedding-status` | embedding 进度统计 |

**embedding 状态响应**:
```json
{
    "tenant_id": "uuid",
    "stats": {
        "resume": {"pending": 5, "completed": 10},
        "jd": {"pending": 2, "completed": 3},
        "question_bank": {"pending": 0, "completed": 20}
    }
}
```

## 8. 错误响应格式

```json
{
    "detail": "错误描述信息"
}
```

HTTP 状态码:
- 200: 成功
- 201: 创建成功
- 204: 删除成功 (无响应体)
- 400: 请求参数错误
- 401: 未认证
- 403: 无权限
- 404: 资源不存在
- 409: 冲突 (如邮箱已注册)
- 500: 服务器内部错误

## 9. 多租户隔离

所有 API（除认证外）自动注入租户上下文：

```python
@router.get("/resumes")
async def list_resumes(
    tenant: Tenant = Depends(get_current_tenant),  # JWT → tenant
    db: AsyncSession = Depends(get_db),
):
    # tenant.id 自动用于数据过滤
    result = await db.execute(
        select(Resume).where(Resume.tenant_id == tenant.id)
    )
```
