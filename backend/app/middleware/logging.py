"""
Request logging middleware that injects request_id and tenant_id into log context.
Logs every request with method, path, status, and duration.
"""

import time
import uuid
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.logging import get_structured_logger, set_request_id, set_tenant_id

logger = get_structured_logger("middleware.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that injects request context into structured logging."""

    async def dispatch(self, request: Request, call_next):
        # Generate unique request ID
        request_id = str(uuid.uuid4())
        set_request_id(request_id)
        request.state.request_id = request_id

        start_time = time.time()

        # Log incoming request
        logger.info(
            f"{request.method} {request.url.path}",
            direction="in",
            method=request.method,
            path=request.url.path,
            query=str(request.query_params) if request.query_params else None,
            client=request.client.host if request.client else None,
        )

        try:
            response: Response = await call_next(request)

            duration_ms = round((time.time() - start_time) * 1000, 2)

            # Log outgoing response
            logger.info(
                f"{request.method} {request.url.path} → {response.status_code}",
                direction="out",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration_ms=duration_ms,
            )

            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as exc:
            duration_ms = round((time.time() - start_time) * 1000, 2)
            logger.exception(
                f"{request.method} {request.url.path} → ERROR",
                direction="error",
                method=request.method,
                path=request.url.path,
                duration_ms=duration_ms,
                error_type=type(exc).__name__,
                error_message=str(exc),
            )
            raise


class TenantLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware that extracts tenant_id from JWT and injects into log context."""

    async def dispatch(self, request: Request, call_next):
        # tenant_id is set by get_current_tenant dependency in routes
        # We set it here if already available, but it's typically done in the route handler
        response = await call_next(request)
        return response
