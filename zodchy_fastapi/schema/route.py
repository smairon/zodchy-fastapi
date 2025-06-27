import abc
from typing import Callable, Any

class Route(abc.ABC):
    def __init__(
        self,
        path: str,
        methods: list[str],
        tags: list[str],
        **kwargs,
    ):
        self.path = path
        self.methods = methods
        self.tags = tags
        self.kwargs = kwargs
        
class ApiRoute(Route):
    def __init__(
        self,
        path: str,
        endpoint: Callable[..., Any],
        responses: dict[str, Any],
        methods: list[str],
        tags: list[str],
        **kwargs,
    ):
        super().__init__(path, methods, tags, **kwargs)
        self.endpoint = endpoint
        self.responses = responses

class ZodchyRoute(Route):
    def __init__(
        self,
        path: str,
        request_adapter: Callable[..., Any],
        response_adapter: Callable[..., Any],
        methods: list[str],
        tags: list[str],
        **kwargs,
    ):
        super().__init__(path, methods, tags, **kwargs)
        self.request_adapter = request_adapter
        self.response_adapter = response_adapter