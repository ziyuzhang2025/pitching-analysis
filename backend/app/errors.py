"""One error shape for every failure: {"error": {"code", "message", "details"}}."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class APIError(Exception):
    """Raise from handlers/services; rendered by the handler below."""

    def __init__(self, status_code: int, code: str, message: str, details: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class NotFound(APIError):
    def __init__(self, resource: str, resource_id: Any) -> None:
        super().__init__(404, "not_found", f"{resource} {resource_id} not found")


class Conflict(APIError):
    def __init__(self, message: str, details: Any = None) -> None:
        super().__init__(409, "conflict", message, details)


class NotImplementedYet(APIError):
    """Placeholder for exercise endpoints (docs/backend_exercises.md)."""

    def __init__(self, exercise: str) -> None:
        super().__init__(501, "not_implemented", f"Not implemented yet: {exercise}")


def error_body(code: str, message: str, details: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "details": details}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def _api_error(_: Request, exc: APIError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code,
                            content=error_body(exc.code, exc.message, exc.details))

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        details = [
            {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
            for e in exc.errors()
        ]
        return JSONResponse(status_code=422,
                            content=error_body("validation_error", "Invalid request", details))

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "not_found" if exc.status_code == 404 else "http_error"
        return JSONResponse(status_code=exc.status_code, content=error_body(code, str(exc.detail)))

    @app.exception_handler(NotImplementedError)
    async def _not_impl(_: Request, exc: NotImplementedError) -> JSONResponse:
        message = str(exc) or "Not implemented yet"
        return JSONResponse(status_code=501, content=error_body("not_implemented", message))
