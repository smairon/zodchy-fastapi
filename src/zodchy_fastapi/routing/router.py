import collections.abc
from typing import Any

import fastapi

from ..definition.contracts import (
    EndpointContract,
    PypelineRegistryContract,
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
            status_code: {"model": response_model}
            for status_code, response_model in self._endpoint.response.get_schema()
        }


class Router:
    def __init__(
        self,
        router: fastapi.APIRouter,
        pipeline_registry: PypelineRegistryContract,
    ):
        self._router = router
        self._pipeline_registry = pipeline_registry

    def __call__(self, routes: collections.abc.Iterable[RouteContract]) -> fastapi.APIRouter:
        for route in routes:
            self._register_route(route)
        return self._router

    def _register_route(
        self,
        route: RouteContract,
    ) -> None:
        self._router.add_api_route(
            path=route.path,
            endpoint=route.endpoint(self._pipeline_registry),
            responses=route.responses,  # type: ignore
            methods=route.methods,
            tags=list(route.tags) if route.tags is not None else None,
            **route.params,
        )
