import abc
from collections.abc import Callable, Collection
from functools import cached_property
from typing import Annotated, Any, TypeAlias, cast

from fastapi import Depends, Request
from zodchy.codex.cqea import Message
from zodchy.toolbox.notation import ParserContract as QueryNotationParserContract

from .definition.contracts import RequestAdapterContract, RequestParameterContract
from .definition.schema.request import FilterParam, RequestData, RequestModel

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
        self._value = ...
        self._serializer = serializer or self._default_serializer

    def set_value(self, value: Any) -> None:
        self._value = value

    def get_name(self) -> str:
        return self._name

    def get_type(self) -> type:
        return self._type

    def __call__(self) -> SerializationResultType:
        if self._value is ...:
            raise ValueError(f"No value set for parameter {self._name}")
        return self._serializer(self._value)  # type: ignore

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
        data = value.data if hasattr(value, "data") else value  # type: ignore
        if isinstance(data, list):
            return [self._dump_model(cast(RequestModel, item)) for item in data]
        else:
            return self._dump_model(cast(RequestModel, data))

    def _dump_model(self, model: RequestModel | RequestData | dict) -> dict[str, Any]:
        if isinstance(model, dict):
            return model
        data = model.model_dump(
            include=self._include,
            exclude=self._exclude,
            exclude_none=self._exclude_none,
            exclude_unset=self._exclude_unset,
        )
        return data


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
            for t in self._notation_parser(value.model_dump(exclude_none=True, exclude_unset=True), self._types_map)
        }

    def get_type(self) -> Annotated[type, Depends]:
        return Annotated[self._type, Depends()]  # type: ignore

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
        return {self.get_name(): value}


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
            f"No default handler function for {self.get_name()}. You must provide a custom handler function or do not use this parameter."
        )


class DeclarativeAdapter:
    def __init__(self, message_type: type[Message], type_cast_map: dict[str, type] | None = None):
        self._message_type = message_type
        self._type_cast_map = type_cast_map or {}
        self._parameters: dict[str, Parameter] = {}

    def __call__(self, **kwargs: Parameter) -> list[Message]:
        data: dict[str, Any] = {}
        result: list[dict[str, Any]] | None = None
        for _, parameter in kwargs.items():
            _data = parameter()
            if isinstance(_data, dict):
                data |= _data
            else:
                result = list(_data)
        if result:
            return [self._message_type(**{**self._type_cast(data), **self._type_cast(item)}) for item in result]
        return [self._message_type(**self._type_cast(data))]

    def _type_cast(self, data: dict[str, Any]) -> dict[str, Any]:
        for field_name, field_type in self._type_cast_map.items():
            if field_name in data:
                data[field_name] = field_type(data[field_name])
        return data


class RequestDescriber:
    def __init__(
        self,
        schema: Collection[RequestParameterContract],
        adapter: RequestAdapterContract,
    ):
        self._adapter = adapter
        self._schema = schema

    def get_adapter(self) -> RequestAdapterContract:
        return self._adapter

    def get_schema(self) -> Collection[RequestParameterContract]:
        return self._schema
