from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import get_settings

settings = get_settings()

qdrant_client = QdrantClient(url=settings.qdrant_url)

COLLECTIONS = {
    "chunks": {
        "vectors": VectorParams(size=settings.embedding_dimension, distance=Distance.COSINE),
    },
    "questions": {
        "vectors": VectorParams(size=settings.embedding_dimension, distance=Distance.COSINE),
    },
}


def init_qdrant():
    """Initialize Qdrant collections if they don't exist."""
    existing = {c.name for c in qdrant_client.get_collections().collections}
    for name, config in COLLECTIONS.items():
        if name not in existing:
            qdrant_client.create_collection(
                collection_name=name,
                vectors_config=config["vectors"],
            )


def get_qdrant() -> QdrantClient:
    return qdrant_client
