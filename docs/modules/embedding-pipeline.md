# Embedding Pipeline 设计

## 1. 概述

Embedding Pipeline 负责文档 chunk 的向量化，遵循"上传快 + 异步Embedding"的设计原则。

## 2. 设计理念

### 问题
上传大文件（题库PDF可能有几百页）时，实时 embedding 会阻塞请求，用户体验差。

### 方案
```
上传阶段（同步，秒级）:
  文件 → 解析文本 → 分块 → 存入PG(status=pending) → 返回成功

Embedding阶段（异步，分钟级）:
  Celery Worker → 查询pending chunks → 批量embedding → 写入Qdrant → 更新status=completed
```

## 3. 架构

```
┌──────────┐    ┌──────────┐    ┌──────────────┐    ┌─────────┐
│ Upload   │───▶│   PG     │◀───│ Celery Worker │───▶│ Qdrant  │
│ API      │    │ chunks   │    │ (async task)  │    │         │
└──────────┘    │ status:  │    └──────────────┘    └─────────┘
                │ pending  │
                └──────────┘
                       ▲
                       │
                ┌──────┴──────┐
                │ Admin API   │  (手动触发)
                │ trigger-emb │
                └─────────────┘
```

## 4. 核心模块

### 4.1 EmbeddingPipeline

**文件**: `backend/app/services/embedding_pipeline.py`

```python
class EmbeddingPipeline:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.embeddings = get_embeddings()  # LangChain Embeddings 接口
        self.qdrant = get_qdrant()

    async def save_chunks(tenant_id, source_type, source_id, chunks) → None
        # 将chunks写入PG，status=pending

    def trigger_embedding(source_type, source_id) → None
        # 发送Celery任务

    async def process_chunks(source_type, source_id, batch_size=20) → None
        # 查询pending chunks → 批量embed → upsert Qdrant → 更新status

    async def process_all_pending(source_type=None, tenant_id=None) → None
        # 处理所有pending chunks（Admin手动触发）
```

### 4.2 Celery 任务

**文件**: `backend/app/tasks/embedding_tasks.py`

```python
@celery_app.task(name="embed_source_chunks")
def embed_source_chunks(source_type: str, source_id: str):
    """处理单个文档的pending chunks"""

@celery_app.task(name="embed_all_pending")
def embed_all_pending(source_type: str = None, tenant_id: str = None):
    """批量处理所有pending chunks（Admin触发）"""
```

### 4.3 触发方式

| 触发方式 | 时机 | 说明 |
|----------|------|------|
| 自动 | 文件上传完成后 | API 中直接调用 `pipeline.trigger_embedding()` |
| 手动 | Admin API | `POST /api/v1/admin/trigger-embedding?source_type=resume` |
| 批量 | 系统初始化 | `POST /api/v1/admin/trigger-embedding` (无过滤，处理全部pending) |

## 5. 数据流

### 5.1 单个文档处理

```
1. API接收文件
2. DocumentParser.parse() → raw_text
3. Chunker.chunk(raw_text, strategy) → chunks[]
4. EmbeddingPipeline.save_chunks() → PG (status=pending)
5. EmbeddingPipeline.trigger_embedding() → Celery任务
6. [异步] Celery Worker:
   a. SELECT * FROM document_chunks
      WHERE source_type=? AND source_id=? AND embedding_status='pending'
      ORDER BY chunk_index
   b. 批量调用 embeddings.embed_documents(texts)
   c. Qdrant.upsert(points)
   d. UPDATE document_chunks SET embedding_status='completed', qdrant_point_id=?
```

### 5.2 批量处理（Admin触发）

```
1. Admin API接收请求
2. Celery任务查询所有 status='pending' 的chunks
3. 按 (source_type, source_id) 分组
4. 每批20条并发embed + upsert
5. 更新所有chunks为completed
```

## 6. 状态管理

```
pending ──→ processing ──→ completed
                │
                └──→ failed ──→ (重新触发) → pending
```

- `pending`: 已保存，等待embedding
- `processing`: Celery正在处理
- `completed`: 已写入Qdrant
- `failed`: embedding失败，需重试

## 7. Embedding 模型配置

通过 LangChain Embeddings 接口适配多种供应商：

```python
# 环境变量
EMBEDDING_PROVIDER=openai           # openai | huggingface | local
EMBEDDING_MODEL=text-embedding-3-large

# 工厂方法
def get_embeddings() -> Embeddings:
    if provider == "openai":
        return OpenAIEmbeddings(model=settings.embedding_model)
    # 可扩展其他供应商...
```

**向量维度说明**:
- `text-embedding-3-large`: 3072维
- `text-embedding-3-small`: 1536维
- `bge-large-zh-v1.5`: 1024维

Qdrant Collection 创建时需匹配向量维度。

## 8. 文档分块策略

**文件**: `backend/app/services/document_parser.py::Chunker`

| 文档类型 | 策略 | chunk_size | overlap |
|----------|------|-----------|---------|
| resume | RecursiveCharacterTextSplitter | 500 | 50 |
| jd | 按章节/段落分割 + 过长时递归分块 | 600 | 50 |
| question_bank | 正则识别题号分割 + 过长时递归分块 | 800 | 50 |

**题库分割正则**: `\n(?=\d+[.、)）]|\n(?=[Qq]uestion\s*\d+)`

## 9. 性能考虑

- Celery Worker 并发数: 2（`docker-compose.yml` 中配置 `-c 2`）
- 批量 embedding: 每批 20 条，减少 API 调用次数
- Qdrant upsert: 批量写入，支持幂等更新
- 向量维度匹配: 创建 Collection 时指定正确的 vector size
