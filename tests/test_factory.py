from typing import Any, cast

import pydantic
import pytest

from zodchy_fastapi.definition.schema.request import RequestData, RequestModel
from zodchy_fastapi.definition.schema.response import ResponseData, ResponseModel
from zodchy_fastapi.factory import make_request_class, make_response_class


class SampleData(pydantic.BaseModel):
    """Sample pydantic model to use as data class in factory functions."""

    name: str
    value: int


class SampleResponseData(ResponseData):
    """Sample response data class for testing."""

    message: str


class SampleRequestData(RequestData):
    """Sample request data class for testing."""

    payload: str


# Type alias for dynamically created request classes
# mypy cannot infer types of dynamically created classes,
# so we use Any for runtime instantiation and cast for assertions


# --------------- Tests for make_response_class ---------------


def test_make_response_class_creates_class_with_correct_name() -> None:
    """Test that make_response_class creates a class with the correct naming convention."""
    response_class = make_response_class(SampleData)

    assert response_class.__name__ == "SampleDataResponse"


def test_make_response_class_inherits_from_response_model() -> None:
    """Test that the created class is a subclass of ResponseModel."""
    response_class = make_response_class(SampleData)

    assert issubclass(response_class, ResponseModel)


def test_make_response_class_has_correct_annotations() -> None:
    """Test that the created class has correct type annotations for 'data' field."""
    response_class = make_response_class(SampleData)

    assert "data" in response_class.__annotations__
    assert response_class.__annotations__["data"] is SampleData


def test_make_response_class_can_instantiate_with_data() -> None:
    """Test that the created response class can be instantiated with data."""
    response_class = make_response_class(SampleData)

    # Create an instance with valid data
    data = SampleData(name="test", value=42)
    instance = response_class(data=data)

    assert instance.data == data
    assert instance.data.name == "test"
    assert instance.data.value == 42


def test_make_response_class_validates_data_type() -> None:
    """Test that the created response class validates data types correctly."""
    response_class = make_response_class(SampleData)

    # Valid data should work
    valid_data = SampleData(name="valid", value=100)
    instance = response_class(data=valid_data)
    assert instance.data == valid_data


def test_make_response_class_with_response_data_subclass() -> None:
    """Test make_response_class with a ResponseData subclass."""
    response_class = make_response_class(SampleResponseData)

    assert response_class.__name__ == "SampleResponseDataResponse"
    assert issubclass(response_class, ResponseModel)

    data = SampleResponseData(message="Hello, World!")
    instance = response_class(data=data)
    assert instance.data.message == "Hello, World!"


def test_make_response_class_returns_different_classes_for_different_inputs() -> None:
    """Test that make_response_class returns unique classes for different data classes."""

    class AnotherData(pydantic.BaseModel):
        field: str

    response_class_a = make_response_class(SampleData)
    response_class_b = make_response_class(AnotherData)

    assert response_class_a is not response_class_b
    assert response_class_a.__name__ == "SampleDataResponse"
    assert response_class_b.__name__ == "AnotherDataResponse"


def test_make_response_class_serializes_to_dict() -> None:
    """Test that instances of the created response class can be serialized to dict."""
    response_class = make_response_class(SampleData)
    data = SampleData(name="serialize_test", value=999)
    instance = response_class(data=data)

    serialized = instance.model_dump()

    assert serialized == {"data": {"name": "serialize_test", "value": 999}}


def test_make_response_class_serializes_to_json() -> None:
    """Test that instances of the created response class can be serialized to JSON."""
    response_class = make_response_class(SampleData)
    data = SampleData(name="json_test", value=123)
    instance = response_class(data=data)

    json_str = instance.model_dump_json()

    assert '"name":"json_test"' in json_str
    assert '"value":123' in json_str


# --------------- Tests for make_request_class ---------------


def test_make_request_class_creates_class_with_correct_name() -> None:
    """Test that make_request_class creates a class with the correct naming convention."""
    request_class = make_request_class(SampleData)

    assert request_class.__name__ == "SampleDataRequest"


def test_make_request_class_inherits_from_request_model() -> None:
    """Test that the created class is a subclass of RequestModel."""
    request_class = make_request_class(SampleData)

    assert issubclass(request_class, RequestModel)


def test_make_request_class_has_correct_annotations() -> None:
    """Test that the created class has correct type annotations for 'data' field."""
    request_class = make_request_class(SampleData)

    assert "data" in request_class.__annotations__
    assert request_class.__annotations__["data"] is SampleData


def test_make_request_class_can_instantiate_with_data() -> None:
    """Test that the created request class can be instantiated with data."""
    request_class = make_request_class(SampleData)

    # Create an instance with valid data
    data = SampleData(name="test", value=42)
    instance = request_class(data=data)

    assert instance.data == data
    assert instance.data.name == "test"
    assert instance.data.value == 42


def test_make_request_class_validates_data_type() -> None:
    """Test that the created request class validates data types correctly."""
    request_class = make_request_class(SampleData)

    # Valid data should work
    valid_data = SampleData(name="valid", value=100)
    instance = request_class(data=valid_data)
    assert instance.data == valid_data


def test_make_request_class_with_request_data_subclass() -> None:
    """Test make_request_class with a RequestData subclass."""
    request_class = make_request_class(SampleRequestData)

    assert request_class.__name__ == "SampleRequestDataRequest"
    assert issubclass(request_class, RequestModel)

    data = SampleRequestData(payload="test payload")
    instance = request_class(data=data)
    assert instance.data.payload == "test payload"


def test_make_request_class_returns_different_classes_for_different_inputs() -> None:
    """Test that make_request_class returns unique classes for different data classes."""

    class AnotherData(pydantic.BaseModel):
        field: str

    request_class_a = make_request_class(SampleData)
    request_class_b = make_request_class(AnotherData)

    assert request_class_a is not request_class_b
    assert request_class_a.__name__ == "SampleDataRequest"
    assert request_class_b.__name__ == "AnotherDataRequest"


def test_make_request_class_serializes_to_dict() -> None:
    """Test that instances of the created request class can be serialized to dict."""
    request_class = make_request_class(SampleData)
    data = SampleData(name="serialize_test", value=999)
    instance = request_class(data=data)

    serialized = instance.model_dump()

    assert serialized == {"data": {"name": "serialize_test", "value": 999}}


def test_make_request_class_serializes_to_json() -> None:
    """Test that instances of the created request class can be serialized to JSON."""
    request_class = make_request_class(SampleData)
    data = SampleData(name="json_test", value=123)
    instance = request_class(data=data)

    json_str = instance.model_dump_json()

    assert '"name":"json_test"' in json_str
    assert '"value":123' in json_str


# --------------- Integration/Edge Case Tests ---------------


def test_factory_functions_work_with_nested_models() -> None:
    """Test that factory functions work correctly with nested pydantic models."""

    class NestedData(pydantic.BaseModel):
        inner_value: int

    class OuterData(pydantic.BaseModel):
        nested: NestedData
        label: str

    response_class = make_response_class(OuterData)
    request_class = make_request_class(OuterData)

    nested = NestedData(inner_value=10)
    outer = OuterData(nested=nested, label="outer")

    response_instance = response_class(data=outer)
    request_instance = request_class(data=outer)

    assert response_instance.data.nested.inner_value == 10
    assert request_instance.data.label == "outer"


def test_factory_functions_work_with_optional_fields() -> None:
    """Test that factory functions work with models containing optional fields."""

    class OptionalData(pydantic.BaseModel):
        required_field: str
        optional_field: int | None = None

    response_class = make_response_class(OptionalData)
    request_class = make_request_class(OptionalData)

    # Without optional field
    data_without_optional = OptionalData(required_field="required")
    response_instance = response_class(data=data_without_optional)
    assert response_instance.data.optional_field is None

    # With optional field
    data_with_optional = OptionalData(required_field="required", optional_field=42)
    request_instance = request_class(data=data_with_optional)
    assert request_instance.data.optional_field == 42


def test_factory_functions_work_with_list_fields() -> None:
    """Test that factory functions work with models containing list fields."""

    class ListData(pydantic.BaseModel):
        items: list[str]
        counts: list[int]

    response_class = make_response_class(ListData)

    data = ListData(items=["a", "b", "c"], counts=[1, 2, 3])
    instance = response_class(data=data)

    assert instance.data.items == ["a", "b", "c"]
    assert instance.data.counts == [1, 2, 3]


def test_factory_functions_with_empty_model() -> None:
    """Test that factory functions work with models that have no fields."""

    class EmptyData(pydantic.BaseModel):
        pass

    response_class = make_response_class(EmptyData)
    request_class = make_request_class(EmptyData)

    data = EmptyData()
    response_instance = response_class(data=data)
    request_instance = request_class(data=data)

    assert response_instance.data is not None
    assert request_instance.data is not None


def test_created_classes_are_valid_pydantic_models() -> None:
    """Test that created classes are fully functional pydantic models."""
    response_class = make_response_class(SampleData)
    request_class = make_request_class(SampleData)

    # Check model_fields attribute exists (pydantic v2)
    assert hasattr(response_class, "model_fields")
    assert hasattr(request_class, "model_fields")

    # Check that 'data' is in model_fields
    assert "data" in response_class.model_fields
    assert "data" in request_class.model_fields


def test_make_response_class_return_type() -> None:
    """Test that make_response_class returns correct type."""
    response_class = make_response_class(SampleData)

    # Should be a type (class)
    assert isinstance(response_class, type)

    # Should be usable as a type annotation
    def dummy_function() -> type[ResponseModel[Any]]:
        return response_class

    result = dummy_function()
    assert result is response_class


def test_make_request_class_return_type() -> None:
    """Test that make_request_class returns correct type."""
    request_class = make_request_class(SampleData)

    # Should be a type (class)
    assert isinstance(request_class, type)

    # Should be usable as a type annotation
    def dummy_function() -> type[RequestModel]:
        return request_class

    result = dummy_function()
    assert result is request_class
