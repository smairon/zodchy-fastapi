import dataclasses
from typing import Callable, Any


@dataclasses.dataclass
class ResponseAdapter:
    executable: Callable[..., Any]
    need_request: bool = False


@dataclasses.dataclass
class RequestAdapter:
    executable: Callable[..., Any]
    params: dict[str, type]
    need_request: bool = False