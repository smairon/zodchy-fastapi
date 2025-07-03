import collections.abc
from typing import Callable, Any
import inspect
import fastapi

from ..endpoints import zodchy_endpoint
from ..schema import route
from ..contracts import TaskExecutorContract
from ..internal.contracts import ResponseAdapter, RequestAdapter


class ZodchyRouterFactory():
    def __init__(
        self, 
        task_executor: TaskExecutorContract,
        routes: collections.abc.Iterable[route.Route] | None = None
    ):
        self._task_executor = task_executor
        self._routes = list(routes) if routes else []
        
    def register_routes(self, *routes: route.Route):
        for route in routes:
            self._routes.append(route)
    
    def get_instance(self, **params) -> fastapi.APIRouter:
        router = fastapi.APIRouter(**params)
        for _route in self._routes:
            if isinstance(_route, route.ZodchyRoute):
                router = self._register_zodchy_route(router, _route)
            elif isinstance(_route, route.ApiRoute):
                router = self._register_api_route(router, _route)
            else:
                raise ValueError(f"Invalid route type: {type(_route)}")
        return router
    
    def _register_api_route(self,         
        router: fastapi.APIRouter,
        route: route.ApiRoute
    ) -> fastapi.APIRouter:
        router.add_api_route(
            path=route.path,
            endpoint=route.endpoint,
            responses=route.responses,
            methods=route.methods,
            tags=route.tags,
            **route.kwargs,
        )
        return router
    
    def _register_zodchy_route(
        self,
        router: fastapi.APIRouter,
        route: route.ZodchyRoute,
    ) -> fastapi.APIRouter:
        response_adapter = self._build_reponse_adapter(route.response_adapter)
        request_adapter = self._build_request_adapter(route.request_adapter)
        router.add_api_route(
            path=route.path,
            endpoint=zodchy_endpoint(
                request_adapter=request_adapter,
                response_adapter=response_adapter,
                task_executor=self._task_executor,
            ),
            responses=self._build_responses(response_adapter),
            methods=route.methods,
            tags=route.tags,
            **route.kwargs,
        )
        return router
        
    def _build_responses(self, response_adapter: ResponseAdapter):
        responses = response_adapter.executable.__dict__["__response_schema__"]
        return {k: {"model": v} for k, v in responses.items()}

    def _build_reponse_adapter(self, executable: Callable[..., Any]):
        sig = inspect.signature(executable)
        need_request = False
        for v in sig.parameters.values():
            if v.annotation is fastapi.Request:
                need_request = True

        return ResponseAdapter(
            executable=executable,
            need_request=need_request,
        )

    def _build_request_adapter(self, executable: Callable[..., Any]):
        sig = inspect.signature(executable)
        need_request = False
        params = {}
        for v in sig.parameters.values():
            if v.annotation is fastapi.Request:
                need_request = True
                continue
            params[v.name] = v.annotation
        return RequestAdapter(
            executable=executable,
            params=params,
            need_request=need_request,
        )
