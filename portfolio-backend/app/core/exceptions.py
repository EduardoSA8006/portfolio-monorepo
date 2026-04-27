import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

_logger = logging.getLogger("app.exceptions")


class AppException(Exception):
    status_code: int = 500
    detail: str = "Internal server error"
    code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        detail: str | None = None,
        code: str | None = None,
        extra: dict | None = None,
    ) -> None:
        self.detail = detail or self.__class__.detail
        self.code = code or self.__class__.code
        self.extra: dict = dict(extra) if extra else {}
        super().__init__(self.detail)


def _error_body(code: str, detail: str) -> dict:
    return {"error": code, "detail": detail}


async def _app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    body = _error_body(exc.code, exc.detail)
    # Merge `extra` AFTER the contract fields so a malicious `extra`
    # cannot override `error` or `detail`.
    if exc.extra:
        for key, value in exc.extra.items():
            if key in ("error", "detail"):
                continue
            body[key] = value
    return JSONResponse(
        status_code=exc.status_code,
        content=body,
    )


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code_map = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        422: "UNPROCESSABLE_ENTITY",
        429: "TOO_MANY_REQUESTS",
        500: "INTERNAL_ERROR",
    }
    code = code_map.get(exc.status_code, "HTTP_ERROR")
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_body(code, str(exc.detail)),
    )


async def _validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={"error": "VALIDATION_ERROR", "detail": "Request validation failed", "errors": errors},
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    _logger.exception(
        "unhandled_exception",
        extra={
            "request_id": request_id,
            "path": request.url.path,
            "method": request.method,
        },
    )
    return JSONResponse(
        status_code=500,
        content={**_error_body("INTERNAL_ERROR", "An unexpected error occurred"), "request_id": request_id},
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppException, _app_exception_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
