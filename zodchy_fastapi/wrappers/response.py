import functools
from typing import Callable
from fastapi.responses import Response
from fastapi import Request
from ..schema.response import (
    ResponseModel,
    InternalServerErrorResponseModel,
    NotAuthorizedResponseModel,
    NotFoundResponseModel,
    ForbiddenResponseModel,
    ValidationErrorResponseModel,
    ConflictResponseModel,
)
from ..adapters.exceptions import exception_response_adapter
from ..contracts import ResponseError

type StatusCode = int


class ResponseAdapterWrapper:
    def __init__(
        self,
        responses: dict[StatusCode, type[ResponseModel]] = {
            200: None,
            401: NotAuthorizedResponseModel,
            404: NotFoundResponseModel,
            500: InternalServerErrorResponseModel,
            403: ForbiddenResponseModel,
            400: ValidationErrorResponseModel,
            409: ConflictResponseModel,
        },
        exception_response_adapter: (
            Callable[[Request, Exception], Response] | None
        ) = exception_response_adapter,
    ):
        self._responses = responses
        self._exception_response_adapter = exception_response_adapter

    def add_response(self, status_code: StatusCode, model: type[ResponseModel]):
        self._responses[status_code] = model
        return self

    def __call__(
        self,
        success_model: type[ResponseModel],
        success_status_code: StatusCode = 200,
        error_status_codes: list[StatusCode] = [401, 404, 409, 500],
    ):
        def decorator(func):
            func.__dict__["__response_schema__"] = {
                success_status_code: success_model
            } | {code: self._responses[code] for code in error_status_codes}

            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except ResponseError as e:
                    if self._exception_response_adapter:
                        return self._exception_response_adapter(e)
                    raise e

            return wrapper

        return decorator
