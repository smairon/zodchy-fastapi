import abc
import inspect
from collections.abc import Callable, Collection
from functools import cached_property
from typing import Any, TypeAlias

from fastapi import Request
from zodchy.codex.cqea import Message
from zodchy.toolbox.notation import ParserContract as QueryNotationParserContract

from .definition.schema.request import FilterParam, RequestModel

FieldName: TypeAlias = str
SerializationResultType: TypeAlias = dict[FieldName, Any] | list[dict[FieldName, Any]]
SerializerType: TypeAlias = Callable[[Any], SerializationResultType]


class Parameter(abc.ABC):
    def __init__(
        self,
        type: type,
        name: str,
        serializer: SerializerType | None = None,
    ):
        self._name = name
        self._type = type
        self._serializer = serializer or self._default_serializer

    @property
    def name(self) -> str:
        return self._name

    @property
    def type(self) -> type:
        return self._type

    def __call__(self, value: Any) -> SerializationResultType:
        return self._serializer(value)

    @abc.abstractmethod
    def _default_serializer(self, value: Any) -> SerializationResultType:
        raise NotImplementedError


class ModelParameter(Parameter):
    def __init__(
        self,
        type: type[RequestModel],
        name: str = "model",
        include: set[str] | None = None,
        exclude: set[str] | None = None,
        exclude_none: bool = False,
        exclude_unset: bool = True,
        serializer: SerializerType | None = None,
    ):
        self._include = include
        self._exclude = exclude
        self._exclude_none = exclude_none
        self._exclude_unset = exclude_unset
        super().__init__(type, name, serializer)


    def _default_serializer(self, value: RequestModel) -> SerializationResultType:
        data = value.data
        if isinstance(data, list):
            return [
                item.model_dump(
                    include=self._include,
                    exclude=self._exclude,
                    exclude_none=self._exclude_none,
                    exclude_unset=self._exclude_unset,
                )
                for item in data
            ]
        else:
            return value.model_dump(
                include=self._include,
                exclude=self._exclude,
                exclude_none=self._exclude_none,
                exclude_unset=self._exclude_unset,
            )


class QueryParameter(Parameter):
    def __init__(
        self,
        name: str,
        model_type: type[RequestModel],
        notation_parser: QueryNotationParserContract,
        fields_map: dict[str, str] | None = None,
        serializer: SerializerType | None = None,
    ):
        super().__init__(model_type, name, serializer)
        self._notation_parser = notation_parser
        self._fields_map = fields_map or {}


    def _default_serializer(self, value: RequestModel) -> dict[FieldName, Any]:
        return {
            self._fields_map.get(t[0], t[0]): t[1]
            for t in self._notation_parser(
                value.model_dump(exclude_none=True, exclude_unset=True), self._types_map
            )
        }

    @cached_property
    def _types_map(self) -> dict[str, type]:
        result = {}
        # Ensure self._type is a Pydantic model class with model_fields attribute
        model_cls = self._type
        if hasattr(model_cls, "model_fields"):
            for field_name, field_info in model_cls.model_fields.items():
                for e in getattr(field_info, "metadata", []):
                    if isinstance(e, FilterParam):
                        result[field_name] = e.type
                        break
        return result


class RouteParameter(Parameter):
    def __init__(
        self,
        name: str,
        type: type,
        type_cast: bool = False,
        serializer: SerializerType | None = None,
    ):
        super().__init__(type, name, serializer)
        self._type_cast = type_cast

    def _default_serializer(self, value: Any) -> dict[FieldName, Any]:
        if self._type_cast:
            value = self._type(value)
        return {self.name: value}


class RequestParameter(Parameter):
    def __init__(
        self,
        name: str = "request",
        type: type[Request] = Request,
        serializer: SerializerType | None = None,
    ):
        super().__init__(type, name, serializer)

    def _default_serializer(self, value: Request) -> dict[FieldName, Request]:
        raise NotImplementedError(
            f"No default handler function for {self.name}. You must provide a custom handler function or do not use this parameter."
        )


class DeclarativeAdapter:
    def __init__(self, parameters: Collection[Parameter], message_type: type[Message]):
        self._message_type = message_type
        self._parameters = {p.name: p for p in parameters}

    def route_params(self) -> dict[str, type]:
        return {p.name: p.type for p in self._parameters.values()}

    def __call__(self, **kwargs: Any) -> list[Message] | None:
        data: dict = {}
        result = []
        for name, value in kwargs.items():
            _data = self._parameters[name](value)
            if isinstance(_data, dict):
                data |= _data
            else:
                result = _data
        if result:
            for item in result:
                return [self._message_type(**{**data, **item})]
        else:
            return [self._message_type(**data)]
        return None


class BuilderAdapter:
    def __init__(
        self,
        builder: Callable[..., list[Message]],
    ):
        self._builder = builder

    def route_params(self) -> dict[str, type]:
        parameters = inspect.signature(self._builder).parameters
        return {p.name: p.annotation for p in parameters.values() if p.annotation is not Request}

    def __call__(self, **kwargs: Any) -> list[Message]:
        return self._builder(**kwargs)
