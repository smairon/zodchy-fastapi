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


class HandlerKind(enum.Enum):
    ERROR = enum.auto()
    EVENT = enum.auto()


class ParameterKind(enum.Enum):
    DOMAIN = enum.auto()
    DEPENDENCY = enum.auto()


class ExecutorKind(enum.Enum):
    ASYNC = enum.auto()
    SYNC = enum.auto()


@dataclasses.dataclass(frozen=True)
class HandlerParameter:
    kind: ParameterKind
    name: str
    type: type


@dataclasses.dataclass(frozen=True)
class Executor:
    kind: ExecutorKind
    callable: EventHandlerContract | ErrorHandlerContract


@dataclasses.dataclass
class HandlerEntry:
    kind: HandlerKind
    executor: Executor
    domain_params: collections.abc.Mapping[str, HandlerParameter]
    dependency_params: collections.abc.Iterable[HandlerParameter] | None = None


class ResponseAdapter:
    def __init__(
        self,
        di_container: zodchy.codex.di.DIContainerContract | None = None,
        default_error_status_code: int = 500,
        default_error_message: str = 'Something happens. To have more information about errors, please adjust error_adapter',
    ):
        self._registry = {}
        self._di_container = di_container
        self._default_error_status_code = default_error_status_code
        self._default_error_message = default_error_message

    def register_handler(self, handler: EventHandlerContract | ErrorHandlerContract) -> typing.NoReturn:
        if '__skip_handler__' in handler.__dict__:
            return
        signature = inspect.signature(handler)
        if signature.parameters is None:
            raise Exception('Adapter must have at least one event or error type as parameter')

        handler_kind = None
        params = {
            ParameterKind.DOMAIN: {},
            ParameterKind.DEPENDENCY: {}
        }
        for p in signature.parameters.values():
            if handler_kind is HandlerKind.ERROR and zodchy.codex.cqea.Event in p.annotation.__mro__:
                raise Exception('Cannot mix error and event parameters')
            if handler_kind is HandlerKind.EVENT and zodchy.codex.cqea.Error in p.annotation.__mro__:
                raise Exception('Cannot mix error and event parameters')
            if zodchy.codex.cqea.Error in p.annotation.__mro__:
                handler_kind = HandlerKind.ERROR
                parameter_kind = ParameterKind.DOMAIN
            elif zodchy.codex.cqea.Event in p.annotation.__mro__:
                handler_kind = HandlerKind.EVENT
                parameter_kind = ParameterKind.DOMAIN
            else:
                if self._di_container is None:
                    raise Exception('DI container is mandatory to process dependencies')
                parameter_kind = ParameterKind.DEPENDENCY
            params[parameter_kind][p.annotation.__name__] = HandlerParameter(
                kind=parameter_kind,
                name=p.name,
                type=p.annotation
            )

        if handler_kind is HandlerKind.EVENT:
            if (response_model := handler.__dict__.get('__response_model__')) is None:
                raise Exception('Event adapter must have a valid response model')
            self._registry[response_model.__name__] = HandlerEntry(
                kind=handler_kind,
                executor=Executor(kind=self._derive_executor_kind(handler), callable=handler),
                domain_params=params[ParameterKind.DOMAIN],
                dependency_params=params[ParameterKind.DEPENDENCY].values() or None
            )
        elif handler_kind is HandlerKind.ERROR:
            if len(params[ParameterKind.DOMAIN]) > 1:
                raise Exception("Adapter error handler must have only one error message as parameter")
            for error_type in params[ParameterKind.DOMAIN].keys():
                self._registry[error_type] = HandlerEntry(
                    kind=handler_kind,
                    executor=Executor(kind=self._derive_executor_kind(handler), callable=handler),
                    domain_params=params[ParameterKind.DOMAIN],
                    dependency_params=params[ParameterKind.DEPENDENCY].values() or None
                )
        else:
            raise Exception(f"Unknown handler kind for {handler.__name__}")

    async def __call__(
        self,
        stream: zodchy.codex.cqea.EventStream,
        response_model_type: type[ResponseModel] | None = None,
        desired_event_type: type[zodchy.codex.cqea.Event] | None = None
    ) -> fastapi.responses.Response:
        registry_entry = None
        if response_model_type:
            registry_entry = self._registry.get(response_model_type.__name__)
            if registry_entry is None and desired_event_type is not None:
                for _type in response_model_type.__mro__:
                    if registry_entry := self._registry.get(_type.__name__):
                        break
            if registry_entry is None:
                raise Exception(f'No adapter registered for {response_model_type.__name__}')

        domain_params = {}
        for message in stream:
            if isinstance(message, zodchy.codex.cqea.Error):
                return await self._process_error(message)
            elif isinstance(message, zodchy.codex.cqea.Event):
                if desired_event_type is not None:
                    if type(message) is desired_event_type:
                        domain_param = next(iter(registry_entry.domain_params.values()), None)
                        domain_params[domain_param.name] = message
                else:
                    if registry_entry and (
                        domain_param := registry_entry.domain_params.get(message.__class__.__name__)):
                        domain_params[domain_param.name] = message

        if registry_entry:
            return await self._process_events(registry_entry, domain_params)

        return fastapi.responses.Response(status_code=204)

    async def _process_events(
        self,
        registry_entry: HandlerEntry,
        domain_params: dict
    ):
        params = {
            **domain_params,
            **await self._build_dependency_params(registry_entry)
        }
        if registry_entry.executor.kind is ExecutorKind.ASYNC:
            content = await registry_entry.executor.callable(**params)
        else:
            content = registry_entry.executor.callable(**params)

        return content

    async def _process_error(self, error: zodchy.codex.cqea.Error):
        for c in error.__class__.__mro__:
            if registry_entry := self._registry.get(c.__name__):
                domain_parameter = registry_entry.domain_params.get(c.__name__)
                params = {
                    domain_parameter.name: error,
                    **await self._build_dependency_params(registry_entry)
                }
                if registry_entry.executor.kind is ExecutorKind.ASYNC:
                    content = await registry_entry.executor.callable(**params)
                else:
                    content = registry_entry.executor.callable(**params)

                return content
        return None

    async def _build_dependency_params(
        self,
        entry: HandlerEntry
    ):
        result = {}
        if entry.dependency_params:
            async with self._di_container.get_resolver() as resolver:
                for p in entry.dependency_params:
                    result[p.name] = await resolver.resolve(p.type)
        return result

    @staticmethod
    def _derive_executor_kind(
        executor: EventHandlerContract | ErrorHandlerContract
    ) -> ExecutorKind | None:
        if inspect.iscoroutinefunction(executor):
            return ExecutorKind.ASYNC
        elif inspect.isfunction(executor):
            return ExecutorKind.SYNC
        elif hasattr(executor, '__call__'):
            if inspect.iscoroutinefunction(executor.__call__):
                return ExecutorKind.ASYNC
            else:
                return ExecutorKind.SYNC
        return None


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
