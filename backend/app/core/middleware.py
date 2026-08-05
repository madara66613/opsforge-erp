from __future__ import annotations

import logging
import re
import time
from uuid import uuid4

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

logger = logging.getLogger("opsforge.request")
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied_request_id = request.headers.get("X-Request-ID", "")
        request_id = supplied_request_id
        if not REQUEST_ID_PATTERN.fullmatch(request_id):
            request_id = uuid4().hex
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception:
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "endpoint": request.url.path,
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            raise
        finally:
            if status_code != 500:
                logger.info(
                    "request_completed",
                    extra={
                        "request_id": request_id,
                        "method": request.method,
                        "endpoint": request.url.path,
                        "status": status_code,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                        "user_id": getattr(request.state, "user_id", None),
                    },
                )
