import collections.abc
import inspect
from typing import Any

import fastapi
from zodchy.toolbox.processing import AsyncPipelineContract

from .definition.contracts import (
    EndpointContract,
    RequestAdapterContract,
    ResponseAdapterContract,
    ResponseModel,
    RouteContract,
)


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
            status_code: {"model": response_model} for status_code, response_model in self._endpoint.response_adapter
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
        request_adapter: RequestAdapterContract,
        response_adapter: ResponseAdapterContract,
        pipeline: AsyncPipelineContract,
    ):
        self.request_adapter = request_adapter
        self.response_adapter = response_adapter
        self._pipeline = pipeline

    def __call__(self) -> collections.abc.Callable[..., fastapi.Response]:
        async def func(**kwargs: Any) -> fastapi.Response | None:
            tasks = self.request_adapter(**kwargs)
            stream = await self._pipeline(*tasks)
            response = self.response_adapter(stream)
            return await response

        sig = inspect.signature(func)
        _params = [v for v in sig.parameters.values() if v.name != "kwargs"]
        _exists = {v.name for v in _params}
        for name, annotation in self.request_adapter.route_params().items():
            if name in _exists:
                continue
            _exists.add(name)
            _params.append(
                inspect.Parameter(
                    name,
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=annotation,
                    default=inspect.Parameter.empty,
                )
            )
        func.__signature__ = sig.replace(parameters=_params, return_annotation=ResponseModel)  # type: ignore
        return func  # type: ignore
