# 数据库设计

## 1. 概述

- **PostgreSQL 16**: 结构化业务数据（租户、简历、JD、题库、面试、评估）
- **Qdrant**: 向量数据（文档chunks embedding、题库embedding）

## 2. PostgreSQL 表结构

### 2.1 租户表 (tenants)

```sql
CREATE TABLE tenants (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name          VARCHAR(255) NOT NULL,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT now(),
    updated_at    TIMESTAMPTZ DEFAULT now()
);
```

### 2.2 简历表 (resumes)

```sql
CREATE TABLE resumes (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id),
    filename     VARCHAR(500) NOT NULL,
    file_url     VARCHAR(1000) NOT NULL,        -- MinIO object key
    raw_text     TEXT,                           -- 解析后的纯文本
    structured   JSONB,                          -- LLM分析后的结构化数据
    parse_status VARCHAR(20) DEFAULT 'pending',  -- pending/processing/completed/failed
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_resumes_tenant ON resumes(tenant_id);
```

### 2.3 JD表 (jds)

```sql
CREATE TABLE jds (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id    UUID NOT NULL REFERENCES tenants(id),
    filename     VARCHAR(500) NOT NULL,
    file_url     VARCHAR(1000) NOT NULL,
    raw_text     TEXT,
    structured   JSONB,                          -- {title, requirements, responsibilities...}
    parse_status VARCHAR(20) DEFAULT 'pending',
    created_at   TIMESTAMPTZ DEFAULT now(),
    updated_at   TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_jds_tenant ON jds(tenant_id);
```

### 2.4 题库表 (question_banks)

```sql
CREATE TABLE question_banks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id   UUID NOT NULL REFERENCES tenants(id),
    name        VARCHAR(500) NOT NULL,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_qb_tenant ON question_banks(tenant_id);
```

### 2.5 文档Chunk表 (document_chunks)

通用表，存储简历/JD/题库的分块文本及其embedding状态。

```sql
CREATE TABLE document_chunks (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id),
    source_type      VARCHAR(20) NOT NULL,    -- 'resume' | 'jd' | 'question_bank'
    source_id        UUID NOT NULL,            -- 关联的源文档ID
    chunk_index      INT NOT NULL,             -- chunk序号
    content          TEXT NOT NULL,
    metadata         JSONB,                    -- {page, section, ...}
    embedding_status VARCHAR(20) DEFAULT 'pending', -- pending/processing/completed/failed
    qdrant_point_id  UUID,                    -- Qdrant中对应的point id
    created_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_chunks_tenant ON document_chunks(tenant_id);
CREATE INDEX idx_chunks_source ON document_chunks(source_type, source_id);
CREATE INDEX idx_chunks_embedding_status ON document_chunks(embedding_status);
```

**embedding状态机**:
```
pending → processing → completed
                    → failed → (手动重试) → pending
```

### 2.6 面试会话表 (interviews)

```sql
CREATE TABLE interviews (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id        UUID NOT NULL REFERENCES tenants(id),
    resume_id        UUID REFERENCES resumes(id),
    jd_id            UUID REFERENCES jds(id),
    question_bank_id UUID REFERENCES question_banks(id),
    mode             VARCHAR(50) NOT NULL,      -- 'basic' | 'deep' | 'follow_up' | 'stress'
    status           VARCHAR(20) DEFAULT 'active', -- 'active' | 'completed' | 'abandoned'
    started_at       TIMESTAMPTZ DEFAULT now(),
    completed_at     TIMESTAMPTZ,
    created_at       TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_interviews_tenant ON interviews(tenant_id);
```

### 2.7 面试消息表 (interview_messages)

```sql
CREATE TABLE interview_messages (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id  UUID NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    role          VARCHAR(20) NOT NULL,     -- 'interviewer' | 'candidate' | 'system'
    content       TEXT NOT NULL,
    metadata      JSONB,                    -- {evaluation, score, reference_question, topic...}
    created_at    TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_messages_interview ON interview_messages(interview_id);
```

### 2.8 评估报告表 (interview_reports)

```sql
CREATE TABLE interview_reports (
    id             UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    interview_id   UUID NOT NULL REFERENCES interviews(id) UNIQUE,
    tenant_id      UUID NOT NULL REFERENCES tenants(id),
    overall_score  DECIMAL(3,1),            -- 综合评分 0-10
    scores         JSONB,                   -- {technical_depth: 8, communication: 7, ...}
    strengths      TEXT[],
    weaknesses     TEXT[],
    suggestions    TEXT[],
    raw_analysis   TEXT,                    -- LLM原始分析文本
    created_at     TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX idx_reports_tenant ON interview_reports(tenant_id);
```

## 3. Qdrant Collections

### 3.1 Collection: chunks

所有文档（简历/JD/题库）的chunk embedding。

```
Vector size: 3072 (text-embedding-3-large) / 1024 (bge-large-zh-v1.5)
Distance: Cosine

Payload:
{
    "tenant_id": "uuid",
    "source_type": "resume|jd|question_bank",
    "source_id": "uuid",
    "chunk_id": "uuid",
    "content": "原始文本内容",
    "chunk_index": 0
}

索引字段: tenant_id, source_type
```

### 3.2 Collection: questions

题库按题目粒度存储的embedding。

```
Vector size: 3072
Distance: Cosine

Payload:
{
    "tenant_id": "uuid",
    "question_bank_id": "uuid",
    "question": "题目内容",
    "answer": "参考答案",
    "tags": ["Python", "系统设计"],
    "difficulty": "medium"
}

索引字段: tenant_id, tags, difficulty
```

## 4. 多租户查询规范

### PostgreSQL
```python
# 所有查询必须包含 tenant_id 过滤
stmt = select(Model).where(Model.tenant_id == current_tenant.id)
```

### Qdrant
```python
qdrant_client.search(
    collection_name="chunks",
    query_vector=vector,
    query_filter=Filter(
        must=[
            FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id)),
            FieldCondition(key="source_type", match=MatchValue(value=source_type)),
        ]
    ),
)
```

## 5. ER 关系图

```
tenants (1) ──────< (N) resumes
tenants (1) ──────< (N) jds
tenants (1) ──────< (N) question_banks
tenants (1) ──────< (N) interviews
tenants (1) ──────< (N) interview_reports
tenants (1) ──────< (N) document_chunks

resumes (1) ──────< (N) document_chunks   [source_type='resume']
jds (1) ──────< (N) document_chunks       [source_type='jd']
question_banks (1) ──< (N) document_chunks [source_type='question_bank']

interviews (1) ──< (N) interview_messages
interviews (1) ──── (1) interview_reports
```

## 6. 迁移管理

使用 Alembic 管理数据库迁移：

```bash
# 生成迁移
alembic revision --autogenerate -m "description"

# 执行迁移
alembic upgrade head

# 回滚
alembic downgrade -1
```
