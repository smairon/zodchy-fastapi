from collections.abc import Callable, Generator, Sequence
from enum import Enum
from typing import Any, Protocol

from fastapi.responses import Response
from zodchy.codex.cqea import Message
from zodchy.toolbox.processing import AsyncMessageStreamContract

from .schema.response import ResponseModel


class RequestAdapterContract(Protocol):
    def route_params(self) -> dict[str, type]: ...

    def __call__(self, **kwargs: Any) -> list[Message]: ...


class ResponseAdapterContract(Protocol):
    async def __call__(self, stream: AsyncMessageStreamContract) -> Response | None: ...
    def __iter__(self) -> Generator[tuple[int, type[ResponseModel] | None], None, None]: ...


class EndpointContract(Protocol):
    response_adapter: ResponseAdapterContract
    request_adapter: RequestAdapterContract

    def __call__(self) -> Callable[..., Response]: ...


class RouteContract(Protocol):
    path: str
    methods: list[str]
    tags: Sequence[str | Enum] | None
    endpoint: EndpointContract
    params: dict[str, Any]
    responses: dict[int, dict[str, type[ResponseModel]]]
