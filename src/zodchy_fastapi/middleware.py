import abc
import collections.abc

from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


class ExceptionHandler(abc.ABC):
    def __init__(self, response_type: type[Response]) -> None:
        self._response_type = response_type

    @abc.abstractmethod
    def default_exception_handler(self, request: Request, exc: Exception) -> Response:
        raise NotImplementedError

    @abc.abstractmethod
    def validation_exception_handler(self, request: Request, exc: RequestValidationError) -> Response:
        raise NotImplementedError


class JsonExceptionHandler(ExceptionHandler):
    def __init__(self) -> None:
        super().__init__(JSONResponse)

    def default_exception_handler(self, request: Request, exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=self._build_data(
                code=500,
                message=str(exc),
                details={
                    "type": exc.__class__.__name__,
                },
            ),
        )

    def validation_exception_handler(self, request: Request, exc: RequestValidationError) -> JSONResponse:
        details: dict = {}
        for e in exc.errors():
            details = self._merge(details, self._nestify(e["loc"], e["msg"]))
        return JSONResponse(
            status_code=422,
            content=self._build_data(
                code=422,
                message="Validation Error",
                details=details,
            ),
        )

    def _build_data(self, code: int, message: str, details: dict | None = None) -> dict:
        details = details or {}
        return {"code": code, "message": message, "details": details}

    def _nestify(self, data: collections.abc.Sequence[str] | str, value: dict | str) -> dict:
        if len(data) > 1:
            value = self._nestify(data[1:], value)
        return {data[0]: value}

    def _merge(self, d1: dict, d2: dict) -> dict:
        for k, v in d2.items():
            if k in d1 and isinstance(v, dict):
                d1[k] |= v
            else:
                d1[k] = v
        return d1
