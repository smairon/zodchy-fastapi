from collections.abc import Iterable, Mapping
from typing import Any, cast

import pytest
from fastapi import Request

from zodchy.codex.cqea import Message
from zodchy.codex.operator import EQ
from zodchy_fastapi.definition.schema.request import FilterParam, RequestData, RequestModel
from zodchy_fastapi.request import (
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
        return {self._name: value}


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
        exclude_none=True,
    )
    parameter.set_value(request_model)

    serialized = parameter()

    assert isinstance(serialized, dict)
    # Serialized data contains the inner RequestData fields, without None values
    assert "foo" in serialized
    assert "bar" not in serialized  # excluded because of exclude_none=True


def test_model_parameter_serializes_list_payload() -> None:
    data = [
        SampleRequestData(foo=1, bar=2),
        SampleRequestData(foo=3, bar=None),
    ]
    request_model = _sample_request(data=cast(list[RequestData], data))
    parameter = ModelParameter(SampleRequestModel)
    parameter.set_value(request_model)

    serialized = parameter()

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
    parameter.set_value(_sample_request())
    serialized = parameter()

    assert isinstance(serialized, dict)
    assert captured_types[0]["filter_value"] is int
    assert captured_types[0]["alias_field"] is str
    assert isinstance(serialized["external"], EQ)
    assert isinstance(serialized["filter_value"], EQ)


def test_route_parameter_casts_string_input() -> None:
    cast_parameter = RouteParameter("limit", int, type_cast=True)
    cast_parameter.set_value("5")
    plain_parameter = RouteParameter("offset", int, type_cast=False)
    plain_parameter.set_value("7")

    assert cast_parameter() == {"limit": 5}
    assert plain_parameter() == {"offset": "7"}


def test_request_parameter_without_serializer_raises() -> None:
    parameter = RequestParameter()
    parameter.set_value(object())

    with pytest.raises(NotImplementedError):
        parameter()


def test_declarative_adapter_merges_dict_parameters() -> None:
    adapter = DeclarativeAdapter(
        message_type=SampleMessage,
    )
    first_param = DictParameter("first")
    first_param.set_value("alpha")
    second_param = DictParameter("second")
    second_param.set_value("beta")

    result = adapter(first=first_param, second=second_param)

    assert result is not None
    assert isinstance(result[0], SampleMessage)
    assert result[0].payload == {"first": "alpha", "second": "beta"}


def test_declarative_adapter_builds_message_for_each_sequence_item() -> None:
    adapter = DeclarativeAdapter(
        message_type=SampleMessage,
    )
    # Using ListParameter that returns list from __call__
    payload = [SampleRequestData(foo=1, bar=2), SampleRequestData(foo=3, bar=4)]
    request_model = _sample_request(data=cast(list[RequestData], payload))
    model_param = ModelParameter(SampleRequestModel)
    model_param.set_value(request_model)

    result = adapter(model=model_param)

    assert result is not None
    assert len(result) == 2
    assert all(isinstance(item, SampleMessage) for item in result)
