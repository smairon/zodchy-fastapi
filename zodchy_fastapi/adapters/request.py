import dataclasses
import typing
import collections.abc
import inspect
from types import ModuleType

import zodchy.codex.di
from zodchy import codex

from ..schema.request import RequestModel, FilterParam

T = typing.TypeVar('T')

HandlerContract = collections.abc.Callable[
    [RequestModel],
    codex.cqea.Task
]


@dataclasses.dataclass(frozen=True)
class HandlerParameter:
    name: str
    type: type


@dataclasses.dataclass(frozen=True)
class HandlerEntry:
    executable: HandlerContract
    request_model_param: HandlerParameter
    dependency_params: collections.abc.Iterable[HandlerParameter]


class RequestAdapter:
    def __init__(
        self,
        di_container: zodchy.codex.di.DIContainerContract
    ):
        self._di_container = di_container
        self._registry = {}

    def register_handler(self, handler: HandlerContract) -> typing.NoReturn:
        if '__skip_handler__' in handler.__dict__:
            return
        signature = inspect.signature(handler)
        request_model_param = None
        dependency_params = []
        for p in signature.parameters.values():
            if hasattr(p.annotation, '__mro__') and RequestModel in p.annotation.__mro__:
                request_model_param = HandlerParameter(
                    name=p.name,
                    type=p.annotation
                )
            else:
                dependency_params.append(
                    HandlerParameter(
                        name=p.name,
                        type=p.annotation
                    )
                )
        if request_model_param is None:
            raise Exception('Request adapter must have a request model as parameter')

        self._registry[request_model_param.type.__name__] = HandlerEntry(
            executable=handler,
            request_model_param=request_model_param,
            dependency_params=dependency_params
        )

    async def __call__(
        self,
        request_model: RequestModel,
        **context
    ) -> codex.cqea.Task:
        entry = self._registry.get(request_model.__class__.__name__)
        if entry is None:
            raise Exception(f'No adapter registered for {request_model.__class__.__name__}')

        params = {
            entry.request_model_param.name: request_model
        }
        if entry.dependency_params:
            async with self._di_container.get_resolver() as resolver:
                for p in entry.dependency_params:
                    if context and p.name in context:
                        params[p.name] = context[p.name]
                    else:
                        params[p.name] = await resolver.resolve(p.type)

        return entry.executable(**params)


class QueryRequestParser:
    def __init__(
        self,
        notation_parser: zodchy.codex.query.NotationParser
    ):
        self._notation_parser = notation_parser

    def __call__(
        self,
        request_model: RequestModel,
        fields_map: collections.abc.Mapping[str, str] | None = None
    ) -> collections.abc.Mapping[str, zodchy.codex.query.ClauseBit]:
        fields_map = fields_map or {}
        return {
            fields_map.get(t[0], t[0]): t[1] for t in self._notation_parser(
                request_model.model_dump(exclude_none=True, exclude_unset=True),
                self._types_map(request_model)
            )
        }

    @staticmethod
    def _types_map(payload_model: RequestModel):
        result = {}
        for field_name, field_info in payload_model.model_fields.items():
            for e in field_info.metadata:
                if isinstance(e, FilterParam):
                    result[field_name] = e.type
                    break
        return result


def register_module(
    adapter: RequestAdapter,
    module: ModuleType
) -> RequestAdapter:
    for e in inspect.getmembers(module):
        entity = e[1]
        if inspect.ismodule(entity) and module.__name__ in entity.__name__:
            register_module(adapter, entity)
        elif inspect.isfunction(entity) and '__request_handler__' in entity.__dict__:
            adapter.register_handler(entity)
    return adapter
