import dataclasses
import typing
import collections.abc

from zodchy import codex

from .schema import RequestModel, FilterParam

T = typing.TypeVar('T')

AdapterContract = collections.abc.Callable[[RequestModel, type[T]], T]


class Adapter:
    def __init__(
        self,
        query_notation_parser: codex.query.NotationParser
    ):
        self._query_notation_parser = query_notation_parser

    def __call__(
        self,
        request_model: RequestModel,
        target_model: type[codex.cqea.Query] | type[codex.cqea.Command]
    ) -> codex.cqea.Query:
        if codex.cqea.Query in target_model.__mro__:
            return self._fill_query_model(request_model, target_model)
        elif codex.cqea.Command in target_model.__mro__:
            return self._fill_command_model(request_model, target_model)
        else:
            raise TypeError("Invalid target model type")

    def _fill_query_model(
        self,
        request_model: RequestModel,
        target_model: type[codex.cqea.Query]
    ):
        return target_model(
            **{
                t[0]: t[1] for t in self._query_notation_parser(
                    request_model.model_dump(exclude_none=True, exclude_unset=True),
                    self._types_map(request_model)
                )
            }
        )

    @staticmethod
    def _fill_command_model(
        request_model: RequestModel,
        target_model: type[codex.cqea.Command]
    ):
        return target_model(
            **{
                k: v
                for k, v
                in request_model.model_dump(exclude_unset=True).items()
                if k in {f.name for f in dataclasses.fields(target_model)}
            }
        )

    @staticmethod
    def _types_map(payload_model: RequestModel):
        result = {}
        for field_name, field_info in payload_model.model_fields.items():
            for e in field_info.metadata:
                if isinstance(e, FilterParam):
                    result[field_name] = e.type
                    break
        return result
