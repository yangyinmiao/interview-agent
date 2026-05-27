from minio import Minio
from app.core.config import get_settings

settings = get_settings()

minio_client = Minio(
    endpoint=settings.minio_endpoint,
    access_key=settings.minio_access_key,
    secret_key=settings.minio_secret_key,
    secure=settings.minio_secure,
)


def init_minio():
    """Ensure the bucket exists."""
    if not minio_client.bucket_exists(settings.minio_bucket):
        minio_client.make_bucket(settings.minio_bucket)


def get_minio() -> Minio:
    return minio_client
