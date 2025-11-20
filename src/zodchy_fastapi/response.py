from collections.abc import AsyncGenerator, Generator, Mapping
from typing import Any, Protocol, TypeAlias

from fastapi.responses import Response
from zodchy.codex.cqea import Error, Message
from zodchy.toolbox.processing import AsyncMessageStreamContract

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

    @property
    def status_code(self) -> int:
        return self._status_code

    @property
    def desired_type(self) -> type[Message]:
        return self._desired_type

    @property
    def response_model(self) -> type[ResponseModel] | None:
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

    @property
    def status_code(self) -> int:
        return 500

    @property
    def desired_type(self) -> type[Error]:
        return Error

    @property
    def response_model(self) -> type[ResponseModel]:
        return self._model

    def __call__(self, *errors: Error) -> Response:
        status_code = self._search_for_status_code(errors[0])
        return self._response_type(status_code=status_code, content=self._serializer(*errors))

    def _search_for_status_code(self, error: Error) -> StatusCodeType:
        for error_type, status_code in self._mapping.items():
            if isinstance(error, error_type):
                return status_code
        return 500


class Batch:
    def __init__(
        self,
        *messages: Message,
    ):
        self._messages = list(messages) if messages else []

    def append(self, message: Message) -> None:
        self._messages.append(message)

    @property
    def message_type(self) -> type[Message] | None:
        return type(self._messages[0]) if self._messages else None

    def __iter__(self) -> Generator[Message, None, None]:
        yield from self._messages


class DeclarativeAdapter:
    def __init__(
        self,
        *interceptors: Interceptor,
    ):
        self._interceptors = interceptors

    async def __call__(self, stream: AsyncMessageStreamContract) -> Response | None:
        async for batch in self._group_stream(stream):
            for interceptor in self._interceptors:
                if batch.message_type is not None and issubclass(batch.message_type, interceptor.desired_type):
                    return interceptor(*batch)
        return None

    def __iter__(self) -> Generator[tuple[int, type[ResponseModel] | None], None, None]:
        for interceptor in self._interceptors:
            yield interceptor.status_code, interceptor.response_model

    async def _group_stream(self, stream: AsyncMessageStreamContract) -> AsyncGenerator[Batch, None]:
        batch = None
        async for message in stream:
            if batch is None:
                batch = Batch(message)
                continue
            if batch.message_type is not None and isinstance(type(message), batch.message_type):
                batch.append(message)
            else:
                yield batch
                batch = Batch(message)
        if batch is not None:
           yield batch
