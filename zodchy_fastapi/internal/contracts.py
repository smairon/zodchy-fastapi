import dataclasses
import fastapi
from typing import Callable, Any


class ResponseError(Exception):
    def __init__(
        self,
        http_code: int,
        semantic_code: int,
        message: str,
        details: dict | None = None,
    ):
        self.http_code = http_code
        self.message = message
        self.details = details
        self.semantic_code = semantic_code
        super().__init__(self.message)


@dataclasses.dataclass
class ResponseAdapter:
    executable: Callable[..., Any]
    need_request: bool = False


@dataclasses.dataclass
class RequestAdapter:
    executable: Callable[..., Any]
    params: dict[str, type]
