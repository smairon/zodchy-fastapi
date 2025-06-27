from zodchy.codex.cqea.messages import Event, Error, EventStream
from ..contracts import ResponseError

type HttpCode = int


class PanchoStreamHandler:
    def __init__(
        self,
        errors_http_schema: dict[HttpCode, type[Error]],
        default_http_error_code: HttpCode = 500,
        default_error_message: str = "Internal Server Error",
    ):
        self._errors_http_schema = {v: k for k, v in errors_http_schema.items()}
        self._default_http_error_code = default_http_error_code
        self._default_error_message = default_error_message

    def __call__(self, stream: EventStream, desired_event: type[Event]) -> Event:
        result = None
        for event in stream:
            if isinstance(event, Error):
                raise ResponseError(
                    http_code=self._get_http_code(event),
                    semantic_code=(
                        event.status_code if hasattr(event, "status_code") else 0
                    ),
                    message=(
                        event.message
                        if hasattr(event, "message")
                        else "Internal Server Error"
                    ),
                    details=event.details if hasattr(event, "details") else None,
                )
            if isinstance(event, desired_event):
                result = event
        return result

    def _get_http_code(self, event: Error) -> HttpCode:
        for _type in event.__class__.__mro__:
            if _type := self._errors_http_schema.get(_type):
                return _type
        return 500
