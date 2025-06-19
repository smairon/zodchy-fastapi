from typing import Callable, Any
import inspect
import fastapi

from ..endpoints import zodchy_endpoint
from ..internal import contracts


class ZodchyRouter(fastapi.APIRouter):
    def add_zodchy_route(
        self,
        path: str,
        request_adapter: Callable[..., Any],
        response_adapter: Callable[..., Any],
        methods: list[str],
        tags: list[str],
    ):
        response_adapter = self._build_reponse_adapter(response_adapter)
        request_adapter = self._build_request_adapter(request_adapter)
        self.add_api_route(
            path=path,
            endpoint=zodchy_endpoint(
                request_adapter=request_adapter,
                response_adapter=response_adapter,
            ),
            responses=self._build_responses(response_adapter),
            methods=methods,
            tags=tags,
        )
        return self

    def _build_responses(self, response_adapter: contracts.ResponseAdapter):
        responses = response_adapter.executable.__dict__["__response_schema__"]
        return {k: {"model": v} for k, v in responses.items()}

    def _build_reponse_adapter(self, executable: Callable[..., Any]):
        sig = inspect.signature(executable)
        need_request = False
        for v in sig.parameters.values():
            if v.annotation is fastapi.Request:
                need_request = True

        return contracts.ResponseAdapter(
            executable=executable,
            need_request=need_request,
        )

    def _build_request_adapter(self, executable: Callable[..., Any]):
        sig = inspect.signature(executable)
        return contracts.RequestAdapter(
            executable=executable,
            params={k: v.annotation for k, v in sig.parameters.items()}
            | {"request": fastapi.Request},
        )
