import collections.abc
import dataclasses
import enum
import typing
import zodchy
import inspect
import fastapi
from types import ModuleType

from ..schema.response import ResponseModel


class InfoResponse(typing.TypedDict):
    data: collections.abc.Mapping[str, typing.Any]
    meta: collections.abc.Mapping[str, typing.Any] | None


class ErrorResponseData(typing.TypedDict):
    code: int
    message: str
    details: dict | None


class ErrorResponse(typing.TypedDict):
    data: ErrorResponseData


EventHandlerContract: typing.TypeAlias = collections.abc.Callable[
    [zodchy.codex.cqea.Event, ...],
    InfoResponse
]

ErrorHandlerContract: typing.TypeAlias = collections.abc.Callable[
    [zodchy.codex.cqea.Error],
    ErrorResponse
]


@dataclasses.dataclass
class AdapterRegistryEntry:
    handler: EventHandlerContract
    params: collections.abc.Mapping[str, str]


class AdapterKind(enum.Enum):
    ERROR = enum.auto()
    EVENT = enum.auto()


class ResponseAdapter:
    def __init__(
        self,
        response_wrapper: type[fastapi.responses.Response] = fastapi.responses.JSONResponse,
        default_error_status_code: int = 500,
        default_error_message: str = 'Something happens. To have more information about errors, please adjust error_adapter',
    ):
        self._event_handlers_registry = {}
        self._error_handlers_registry = {}
        self._default_error_status_code = default_error_status_code
        self._default_error_message = default_error_message
        self._response_wrapper = response_wrapper

    def register_handler(self, handler: EventHandlerContract | ErrorHandlerContract) -> typing.NoReturn:
        signature = inspect.signature(handler)
        if signature.parameters is None:
            raise Exception('Adapter must have at least one event or error type as parameter')

        adapter_kind = None
        event_adapter_params = {}
        for p in signature.parameters.values():
            if adapter_kind is AdapterKind.ERROR and not isinstance(p.annotation, zodchy.codex.cqea.Error):
                raise Exception('Errors adapter must have only error type as parameter')
            if adapter_kind is AdapterKind.EVENT and not isinstance(p.annotation, zodchy.codex.cqea.Event):
                raise Exception('Events adapter must have only event type as parameter')
            if zodchy.codex.cqea.Error in p.annotation.__mro__:
                adapter_kind = AdapterKind.ERROR
                self._error_handlers_registry[p.annotation.__name__] = handler
            elif zodchy.codex.cqea.Event in p.annotation.__mro__:
                event_adapter_params[p.annotation.__name__] = p.name
                adapter_kind = AdapterKind.EVENT
            else:
                raise Exception('Adapter must have only event or error type as parameter')

        if adapter_kind is AdapterKind.EVENT:
            if (response_model := handler.__dict__.get('__response_model__')) is None:
                raise Exception('Event adapter must have a valid response model')
            self._event_handlers_registry[response_model.__name__] = AdapterRegistryEntry(
                handler=handler,
                params=event_adapter_params
            )

    def __call__(
        self,
        stream: zodchy.codex.cqea.EventStream,
        response_model_type: type[ResponseModel] | None = None
    ) -> fastapi.responses.Response:
        registry_entry = None
        if response_model_type:
            registry_entry = self._event_handlers_registry.get(response_model_type.__name__)
            if registry_entry is None:
                raise Exception(f'No adapter registered for {response_model_type.__name__}')

        params = {}
        for event in stream:
            if isinstance(event, zodchy.codex.cqea.Error):
                for c in event.__class__.__mro__:
                    if handler := self._error_handlers_registry.get(c.__name__):
                        response_data = handler(event)
                        return self._response_wrapper(
                            status_code=handler.__dict__['__status_code__'],
                            content={
                                "data": response_data["data"]
                            }
                        )
                return self._response_wrapper(
                    status_code=self._default_error_status_code,
                    content=self._default_error_message
                )
            elif isinstance(event, zodchy.codex.cqea.Event):
                if registry_entry and (name := registry_entry.params.get(event.__class__.__name__)):
                    params[name] = event

        if registry_entry:
            return self._response_wrapper(
                status_code=registry_entry.handler.__dict__["__status_code__"],
                content=registry_entry.handler(**params)
            )

        return fastapi.responses.Response(status_code=204)


def register_module(
    adapter: ResponseAdapter,
    module: ModuleType
) -> ResponseAdapter:
    for e in inspect.getmembers(module):
        entity = e[1]
        if inspect.ismodule(entity) and module.__name__ in entity.__name__:
            register_module(adapter, entity)
        elif inspect.isfunction(entity) and '__status_code__' in entity.__dict__:
            adapter.register_handler(entity)
    return adapter
