import collections.abc
import inspect
from typing import Any

import fastapi
from zodchy.codex.cqea import Message
from zodchy.toolbox.processing import AsyncPipelineContract

from .definition.contracts import (
    AsyncMessageStreamContract,
    EndpointContract,
    RequestDescriberContract,
    RequestParameterContract,
    ResponseDescriberContract,
    ResponseModel,
    RouteContract,
)


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

    def __iter__(self) -> collections.abc.Generator[Message, None, None]:
        yield from self._messages


class Route:
    def __init__(
        self,
        path: str,
        methods: list[str],
        tags: list[str],
        endpoint: EndpointContract,
        **params: Any,
    ):
        self._path = path
        self._methods = methods
        self._tags = tags
        self._endpoint = endpoint
        self._params = params

    @property
    def path(self) -> str:
        return self._path

    @property
    def methods(self) -> list[str]:
        return self._methods

    @property
    def tags(self) -> list[str]:
        return self._tags

    @property
    def endpoint(self) -> EndpointContract:
        return self._endpoint

    @property
    def params(self) -> dict[str, Any]:
        return self._params

    @property
    def responses(self) -> dict[int, dict[str, Any]]:
        return {
            status_code: {"model": response_model}
            for status_code, response_model in self._endpoint.response.get_schema()
        }


class Router:
    def __init__(
        self,
        router: fastapi.APIRouter,
    ):
        self._router = router

    def __call__(self, routes: collections.abc.Collection[RouteContract]) -> fastapi.APIRouter:
        for route in routes:
            self._register_route(route)
        return self._router

    def _register_route(
        self,
        route: RouteContract,
    ) -> None:
        self._router.add_api_route(
            path=route.path,
            endpoint=route.endpoint(),
            responses=route.responses,  # type: ignore
            methods=route.methods,
            tags=list(route.tags) if route.tags is not None else None,
            **route.params,
        )


class Endpoint:
    def __init__(
        self,
        request: RequestDescriberContract,
        response: ResponseDescriberContract,
        pipeline: AsyncPipelineContract,
    ):
        self.request = request
        self.response = response
        self._pipeline = pipeline

    def __call__(self) -> collections.abc.Callable[..., fastapi.Response]:
        async def func(**kwargs: Any) -> fastapi.Response | None:
            params: dict[str, RequestParameterContract] = {}
            for parameter in self.request.get_schema():
                if parameter.get_name() in kwargs:
                    parameter.set_value(kwargs[parameter.get_name()])
                    params[parameter.get_name()] = parameter
            tasks = self.request.get_adapter()(**params)
            stream = self._pipeline(*tasks)
            async for batch in self._group_stream(stream):
                for interceptor in self.response.get_interceptors():
                    if batch.message_type is not None and issubclass(
                        batch.message_type, interceptor.get_desired_type()
                    ):
                        return interceptor(*batch)
            return None

        sig = inspect.signature(func)
        _params = [v for v in sig.parameters.values() if v.name != "kwargs"]
        _exists = {v.name for v in _params}
        for parameter in self.request.get_schema():
            if parameter.get_name() in _exists:
                continue
            _exists.add(parameter.get_name())
            _params.append(
                inspect.Parameter(
                    parameter.get_name(),
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=parameter.get_type(),
                    default=inspect.Parameter.empty,
                )
            )
        func.__signature__ = sig.replace(parameters=_params, return_annotation=ResponseModel)  # type: ignore
        return func  # type: ignore

    async def _group_stream(self, stream: AsyncMessageStreamContract) -> collections.abc.AsyncGenerator[Batch, None]:
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
