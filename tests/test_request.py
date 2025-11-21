from collections.abc import Iterable, Mapping
from typing import Any, cast

import pytest
from fastapi import Request

from zodchy.codex.cqea import Message
from zodchy.codex.operator import EQ
from zodchy_fastapi.definition.schema.request import FilterParam, RequestData, RequestModel
from zodchy_fastapi.request import (
    BuilderAdapter,
    DeclarativeAdapter,
    ModelParameter,
    Parameter,
    QueryParameter,
    RequestParameter,
    RouteParameter,
)


class SampleRequestData(RequestData):
    foo: int
    bar: int | None = None


class SampleRequestModel(RequestModel):
    filter_value: int
    alias_field: str


# attach FilterParam metadata expected by QueryParameter
SampleRequestModel.model_fields["filter_value"].metadata += (FilterParam(int),)
SampleRequestModel.model_fields["alias_field"].metadata += (FilterParam(str),)


class SampleMessage(Message):
    def __init__(self, **payload: Any) -> None:
        self.payload = payload


class DictParameter(Parameter):
    def __init__(self, name: str):
        super().__init__(dict, name)

    def _default_serializer(self, value: Any) -> dict[str, Any]:
        return {self.name: value}


class ListParameter(Parameter):
    def __init__(self, name: str):
        super().__init__(list, name)

    def _default_serializer(self, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return value


def _sample_request(
    data: RequestData | list[RequestData] | None = None,
    filter_value: int = 10,
    alias_field: str = "alpha",
) -> SampleRequestModel:
    payload: dict[str, Any] = {
        "data": data if data is not None else SampleRequestData(foo=1, bar=None),
        "filter_value": filter_value,
        "alias_field": alias_field,
    }
    return SampleRequestModel(**payload)


def test_model_parameter_serializes_single_instance() -> None:
    request_model = _sample_request()
    parameter = ModelParameter(
        SampleRequestModel,
        include={"data"},
        exclude_none=True,
    )

    serialized = parameter(request_model)

    assert isinstance(serialized, dict)
    assert serialized.keys() == {"data"}
    assert isinstance(serialized["data"], dict)


def test_model_parameter_serializes_list_payload() -> None:
    data = [
        SampleRequestData(foo=1, bar=2),
        SampleRequestData(foo=3, bar=None),
    ]
    request_model = _sample_request(data=cast(list[RequestData], data))
    parameter = ModelParameter(SampleRequestModel)

    serialized = parameter(request_model)

    assert isinstance(serialized, list)
    assert len(serialized) == 2
    assert all(isinstance(item, dict) for item in serialized)


def test_query_parameter_serializes_using_notation_parser() -> None:
    captured_types: list[dict[str, type]] = []

    def parser(
        query: str | Mapping[str, Any],
        types_map: Mapping[str, type],
    ) -> Iterable[tuple[str, EQ[Any]]]:
        captured_types.append(dict(types_map))
        assert isinstance(query, Mapping)
        for key, value in query.items():
            if key == "data":
                continue
            yield key, EQ(value)

    parameter = QueryParameter(
        name="filters",
        model_type=SampleRequestModel,
        notation_parser=parser,
        fields_map={"alias_field": "external"},
    )
    serialized = parameter(_sample_request())

    assert isinstance(serialized, dict)
    assert captured_types[0]["filter_value"] is int
    assert captured_types[0]["alias_field"] is str
    assert isinstance(serialized["external"], EQ)
    assert isinstance(serialized["filter_value"], EQ)


def test_route_parameter_casts_string_input() -> None:
    cast_parameter = RouteParameter("limit", int, type_cast=True)
    plain_parameter = RouteParameter("offset", int, type_cast=False)

    assert cast_parameter("5") == {"limit": 5}
    assert plain_parameter("7") == {"offset": "7"}


def test_request_parameter_without_serializer_raises() -> None:
    parameter = RequestParameter()

    with pytest.raises(NotImplementedError):
        parameter(object())


def test_declarative_adapter_merges_dict_parameters() -> None:
    adapter = DeclarativeAdapter(
        parameters=[DictParameter("first"), DictParameter("second")],
        message_type=SampleMessage,
    )

    result = adapter(first="alpha", second="beta")

    assert result is not None
    assert isinstance(result[0], SampleMessage)
    assert result[0].payload == {"first": "alpha", "second": "beta"}


def test_declarative_adapter_builds_message_for_each_sequence_item() -> None:
    adapter = DeclarativeAdapter(
        parameters=[DictParameter("base"), ListParameter("batch")],
        message_type=SampleMessage,
    )
    payload = [{"detail": "a"}, {"detail": "b"}]

    result = adapter(base="root", batch=payload)

    assert result is not None
    assert len(result) == 2
    assert all(isinstance(item, SampleMessage) for item in result)
    first = cast(SampleMessage, result[0])
    second = cast(SampleMessage, result[1])
    assert first.payload == {"base": "root", "detail": "a"}
    assert second.payload == {"base": "root", "detail": "b"}


def test_builder_adapter_route_params_skip_request_annotation() -> None:
    def builder(item_id: int, request: Request) -> list[Message]:  # pragma: no cover - signature only
        return []

    adapter = BuilderAdapter(builder)

    assert adapter.route_params() == {"item_id": int}


def test_builder_adapter_calls_underlying_builder() -> None:
    def builder(item_id: int) -> list[Message]:
        return [SampleMessage(identifier=item_id)]

    adapter = BuilderAdapter(builder)
    messages = adapter(item_id=42)

    assert len(messages) == 1
    assert isinstance(messages[0], SampleMessage)
    assert messages[0].payload == {"identifier": 42}
