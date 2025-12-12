from collections.abc import Callable
from typing import Any

from fastapi.responses import Response
from zodchy.codex.cqea import Error, Event, Message, View

from ..definition.schema.response import ErrorResponseModel, ResponseData
from ..factory import make_response_class
from ..response import Interceptor
from ..serializing import ResponseMapping, ViewMapping


class InterceptorFactory:
    def __init__(
        self,
        errors_map: dict[int, type[Error]] | None = None,
        default_response_class: type[Response] = Response,
        default_event_serializer: Callable[[Message], Any] | None = None,
        default_error_serializer: Callable[[Error], Any] | None = None,
        default_view_serializer: Callable[[View], Any] | None = None,
    ):
        self._errors_map = errors_map or {}
        self._default_event_serializer = default_event_serializer
        self._default_error_serializer = default_error_serializer
        self._default_view_serializer = default_view_serializer
        self._default_reponse_class = default_response_class

    def error(
        self,
        status_code: int,
        response_class: type[Response] | None = None,
        serializer: Callable[[Error], Any] | None = None,
    ) -> Interceptor:
        response_class = response_class or self._default_reponse_class
        error_serializer = serializer or self._default_error_serializer
        return Interceptor(
            catch=self._errors_map[status_code],
            declare=(status_code, ErrorResponseModel),
            response=(
                response_class,
                ResponseMapping(error_serializer),  # type: ignore
            ),
        )

    def event(
        self,
        event: type[Event],
        response_data: type[ResponseData],
        response_class: type[Response] | None = None,
        serializer: Callable[[Message], Any] | None = None,
    ) -> Interceptor:
        response_class = response_class or self._default_reponse_class
        event_serializer = serializer or self._default_event_serializer
        return Interceptor(
            catch=event,
            declare=(200, make_response_class(response_data)),
            response=(
                response_class,
                ResponseMapping(event_serializer),
            ),
        )

    def list_view(
        self,
        response_data: type[ResponseData],
        response_class: type[Response] | None = None,
        serializer: Callable[[View], Any] | None = None,
    ) -> Interceptor:
        response_class = response_class or self._default_reponse_class
        view_serializer = serializer or self._default_view_serializer
        return Interceptor(
            catch=View,
            declare=(200, make_response_class(list[response_data])),  # type: ignore
            response=(
                response_class,
                ViewMapping(view_serializer),  # type: ignore
            ),
        )

    def item_view(
        self,
        response_data: type[ResponseData],
        response_class: type[Response] | None = None,
        serializer: Callable[[View], Any] | None = None,
    ) -> Interceptor:
        response_class = response_class or self._default_reponse_class
        view_serializer = serializer or self._default_view_serializer
        return Interceptor(
            catch=View,
            declare=(200, make_response_class(response_data)),
            response=(
                response_class,
                ViewMapping(view_serializer),  # type: ignore
            ),
        )
