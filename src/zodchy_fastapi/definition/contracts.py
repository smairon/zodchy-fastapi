from collections.abc import Callable, Collection, Generator
from enum import Enum
from typing import Any, Protocol, TypeAlias

from fastapi.responses import Response
from zodchy.codex.cqea import Message
from zodchy.toolbox.processing import AsyncMessageStreamContract

from .schema.response import ResponseModel


class RequestParameterContract(Protocol):
    def get_name(self) -> str: ...
    def get_type(self) -> type: ...
    def set_value(self, value: Any) -> None: ...
    def __call__(self) -> dict[str, Any] | list[dict[str, Any]]: ...


RequestAdapterContract: TypeAlias = Callable[..., list[Message]]


class ResponseAdapterContract(Protocol):
    async def __call__(self, stream: AsyncMessageStreamContract) -> Response | None: ...
    def __iter__(self) -> Generator[tuple[int, type[ResponseModel] | None], None, None]: ...


class RequestDescriberContract(Protocol):
    def get_adapter(self) -> RequestAdapterContract: ...
    def get_schema(self) -> Collection[RequestParameterContract]: ...


class ResponseInterceptorContract(Protocol):
    def get_status_code(self) -> int: ...

    def get_desired_type(self) -> type[Message]: ...

    def get_response_model(self) -> type[ResponseModel] | None: ...

    def __call__(self, *messages: Message) -> Response: ...


class ResponseDescriberContract(Protocol):
    def get_interceptors(self) -> Collection[ResponseInterceptorContract]: ...
    def get_schema(self) -> Collection[tuple[int, type[ResponseModel] | None]]: ...


class EndpointContract(Protocol):
    request: RequestDescriberContract
    response: ResponseDescriberContract

    def __call__(self) -> Callable[..., Response]: ...


class RouteContract(Protocol):
    path: str
    methods: list[str]
    tags: Collection[str | Enum] | None
    endpoint: EndpointContract
    params: dict[str, Any]
    responses: dict[int, dict[str, type[ResponseModel]]]
