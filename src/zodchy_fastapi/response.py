from collections.abc import Collection, Mapping
from typing import Any, Protocol, TypeAlias

from fastapi.responses import Response
from zodchy.codex.cqea import Error, Message

from .definition.schema.response import ErrorResponseModel, ResponseModel

StatusCodeType: TypeAlias = int
ResponseType: TypeAlias = type[Response]


class SerializerType(Protocol):
    def __call__(self, *messages: Message | Error) -> dict[str, Any]: ...


class Interceptor:
    def __init__(
        self,
        catch: type[Message],
        declare: tuple[StatusCodeType, type[ResponseModel]] | StatusCodeType | None = None,
        response: tuple[ResponseType, SerializerType] | None = None,
    ):
        self._desired_type = catch
        self._status_code = declare[0] if isinstance(declare, tuple) else (declare or 204)
        self._model = declare[1] if declare and isinstance(declare, tuple) else None
        self._serializer = response[1] if response else None
        self._response_type = response[0] if response else None

    def get_status_code(self) -> int:
        return self._status_code

    def get_desired_type(self) -> type[Message]:
        return self._desired_type

    def get_response_model(self) -> type[ResponseModel] | None:
        return self._model

    def __call__(self, *messages: Message) -> Response:
        if not self._serializer or not self._response_type:
            return Response(status_code=self._status_code)
        return self._response_type(status_code=self._status_code, content=self._serializer(*messages))


class ErrorInterceptor:
    def __init__(
        self,
        mapping: Mapping[type[Error], StatusCodeType],
        response: tuple[ResponseType, SerializerType],
        declare: type[ResponseModel] = ErrorResponseModel,
    ):
        self._mapping = mapping
        self._response_type = response[0]
        self._serializer = response[1]
        self._model = declare

    def get_status_code(self) -> int:
        return 500

    def get_desired_type(self) -> type[Error]:
        return Error

    def get_response_model(self) -> type[ResponseModel]:
        return self._model

    def __call__(self, *errors: Error) -> Response:
        status_code = self._search_for_status_code(errors[0])
        return self._response_type(status_code=status_code, content=self._serializer(*errors))

    def _search_for_status_code(self, error: Error) -> StatusCodeType:
        for error_type, status_code in self._mapping.items():
            if isinstance(error, error_type):
                return status_code
        return 500


class ResponseDescriber:
    def __init__(
        self,
        *interceptors: Interceptor,
    ):
        self._interceptors = interceptors

    def get_interceptors(self) -> Collection[Interceptor]:
        return self._interceptors

    def get_schema(self) -> Collection[tuple[int, type[ResponseModel] | None]]:
        return [(interceptor.get_status_code(), interceptor.get_response_model()) for interceptor in self._interceptors]
