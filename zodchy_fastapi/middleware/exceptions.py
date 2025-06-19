import collections.abc

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from ..adapters.exceptions import exception_response_adapter


def default_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return exception_response_adapter(exc)


def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    details: dict = {}
    for e in exc.errors():
        details = _merge(details, _nestify(e["loc"], e["msg"]))
    return exception_response_adapter(exc)


def _nestify(data: collections.abc.Sequence[str] | str, value: str):
    if len(data) > 1:
        value = _nestify(data[1:], value)
    return {data[0]: value}


def _merge(d1: dict, d2: dict):
    for k, v in d2.items():
        if k in d1 and isinstance(v, dict):
            d1[k] |= v
        else:
            d1[k] = v
    return d1
