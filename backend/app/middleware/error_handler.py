# backend/app/middleware/error_handler.py
"""
Global exception handler for FastAPI.
Catches unhandled exceptions and returns structured JSON error responses.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
import traceback
import logging

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """Global error handler middleware."""

    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except ValueError as e:
            logger.warning(f"Validation error: {e}")
            return JSONResponse(
                status_code=400,
                content={
                    "error": "validation_error",
                    "detail": str(e),
                    "status": 400,
                },
            )
        except PermissionError as e:
            logger.warning(f"Permission error: {e}")
            return JSONResponse(
                status_code=403,
                content={
                    "error": "permission_denied",
                    "detail": str(e),
                    "status": 403,
                },
            )
        except FileNotFoundError as e:
            logger.warning(f"File not found: {e}")
            return JSONResponse(
                status_code=404,
                content={
                    "error": "not_found",
                    "detail": str(e),
                    "status": 404,
                },
            )
        except RuntimeError as e:
            # LLM budget exceeded, etc.
            logger.error(f"Runtime error: {e}")
            return JSONResponse(
                status_code=429,
                content={
                    "error": "runtime_error",
                    "detail": str(e),
                    "status": 429,
                },
            )
        except Exception as e:
            logger.error(f"Unhandled error: {e}\n{traceback.format_exc()}")
            return JSONResponse(
                status_code=500,
                content={
                    "error": "internal_server_error",
                    "detail": str(e) if logger.isEnabledFor(logging.DEBUG) else "Internal server error",
                    "status": 500,
                },
            )
