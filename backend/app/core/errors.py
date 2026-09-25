"""Error types and the single error-response format used by every endpoint.

Response body for every error:

    {"error": {"code": "not_found", "message": "...", "details": [...], "request_id": "..."}}

- Validation errors -> 422 with field-level details.
- Known application errors -> their own status code and code string.
- Anything unexpected -> 500 with a generic message; the stack trace goes to logs only.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, request_id_var

logger = get_logger(__name__)


class ErrorDetail(BaseModel):
    field: str | None = None
    message: str


class ErrorBody(BaseModel):
    code: str
    message: str
    details: list[ErrorDetail] = []
    request_id: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class AppError(Exception):
    """Base class for expected, user-reportable errors."""

    status_code: int = status.HTTP_400_BAD_REQUEST
    code: str = "bad_request"

    def __init__(self, message: str, *, details: list[ErrorDetail] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class NotFoundError(AppError):
    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"


class ConflictError(AppError):
    status_code = status.HTTP_409_CONFLICT
    code = "conflict"


class InvalidStateTransitionError(ConflictError):
    code = "invalid_state_transition"


class ExternalServiceError(AppError):
    status_code = status.HTTP_502_BAD_GATEWAY
    code = "external_service_error"


class AgentExecutionError(AppError):
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    code = "agent_execution_error"


class NotImplementedYetError(AppError):
    """Raised by interfaces whose behaviour belongs to a later phase."""

    status_code = status.HTTP_501_NOT_IMPLEMENTED
    code = "not_implemented"


def _body(code: str, message: str, details: list[ErrorDetail] | None = None) -> dict[str, Any]:
    return ErrorResponse(
        error=ErrorBody(
            code=code, message=message, details=details or [], request_id=request_id_var.get()
        )
    ).model_dump()


async def _app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    logger.warning("application error", extra={"code": exc.code, "error_message": exc.message})
    return JSONResponse(status_code=exc.status_code, content=_body(exc.code, exc.message, exc.details))


async def _validation_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        ErrorDetail(
            field=".".join(str(part) for part in err.get("loc", ()) if part != "body") or None,
            message=err.get("msg", "Invalid value"),
        )
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=_body("validation_error", "Request validation failed", details),
    )


async def _http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
    return JSONResponse(status_code=exc.status_code, content=_body(code, str(exc.detail)))


async def _unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("unhandled error", exc_info=exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_body("internal_error", "An unexpected error occurred"),
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(RequestValidationError, _validation_handler)  # type: ignore[arg-type]
    app.add_exception_handler(StarletteHTTPException, _http_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(Exception, _unhandled_handler)
