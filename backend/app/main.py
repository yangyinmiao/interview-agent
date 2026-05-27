from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.qdrant import init_qdrant
from app.core.minio import init_minio
from app.core.logging import get_structured_logger
from app.middleware.logging import RequestLoggingMiddleware

logger = get_structured_logger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    settings = get_settings()
    logger.info("Application starting up", version="0.1.0", debug=settings.debug)

    try:
        init_minio()
        logger.info("MinIO initialized", bucket=settings.minio_bucket)
    except Exception as e:
        logger.warning("MinIO init skipped", reason=str(e))

    try:
        init_qdrant()
        logger.info("Qdrant initialized")
    except Exception as e:
        logger.warning("Qdrant init skipped", reason=str(e))

    yield
    # Shutdown
    logger.info("Application shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        lifespan=lifespan,
    )

    # Request logging must be added first (outermost)
    app.add_middleware(RequestLoggingMiddleware)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router)

    @app.get("/health")
    async def health_check():
        return {"status": "ok", "service": settings.app_name}

    return app


app = create_app()
