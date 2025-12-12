"""
Tests for the interceptors module.
"""

from collections.abc import Callable
from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.responses import JSONResponse, Response
from zodchy.codex.cqea import Error, Event, Message, View

from zodchy_fastapi.definition.schema.response import ErrorResponseModel, ResponseData
from zodchy_fastapi.patterns.interceptors import InterceptorFactory
from zodchy_fastapi.response import Interceptor
from zodchy_fastapi.serializing import ResponseMapping, ViewMapping


# Fixtures and helper classes (not prefixed with Test to avoid pytest collection)


class SampleError400(Error):
    """Sample error for 400 status code."""

    pass


class SampleError404(Error):
    """Sample error for 404 status code."""

    pass


class SampleError500(Error):
    """Sample error for 500 status code."""

    pass


class SampleEvent(Event):
    """Sample event class."""

    def __init__(self, data: Any = None) -> None:
        self._data = data


class SampleView(View):
    """Sample view class."""

    def __init__(self, data: Any, meta: dict[str, Any] | None = None) -> None:
        self._data = data
        self._meta = meta

    def data(self) -> Any:
        return self._data

    def meta(self) -> dict[str, Any] | None:
        return self._meta


class SampleResponseData(ResponseData):
    """Sample response data schema."""

    id: int
    name: str


class SampleItemResponseData(ResponseData):
    """Sample item response data schema."""

    value: str


# Test InterceptorFactory initialization


class TestInterceptorFactoryInit:
    """Tests for InterceptorFactory initialization."""

    def test_init_with_defaults(self) -> None:
        """Test factory initialization with default values."""
        factory = InterceptorFactory()
        assert factory._errors_map == {}
        assert factory._default_event_serializer is None
        assert factory._default_error_serializer is None
        assert factory._default_view_serializer is None
        assert factory._default_reponse_class == Response

    def test_init_with_errors_map(self) -> None:
        """Test factory initialization with errors map."""
        errors_map = {400: SampleError400, 404: SampleError404, 500: SampleError500}
        factory = InterceptorFactory(errors_map=errors_map)
        assert factory._errors_map == errors_map

    def test_init_with_custom_response_class(self) -> None:
        """Test factory initialization with custom response class."""
        factory = InterceptorFactory(default_response_class=JSONResponse)
        assert factory._default_reponse_class == JSONResponse

    def test_init_with_serializers(self) -> None:
        """Test factory initialization with custom serializers."""
        event_serializer = Mock()
        error_serializer = Mock()
        view_serializer = Mock()

        factory = InterceptorFactory(
            default_event_serializer=event_serializer,
            default_error_serializer=error_serializer,
            default_view_serializer=view_serializer,
        )

        assert factory._default_event_serializer == event_serializer
        assert factory._default_error_serializer == error_serializer
        assert factory._default_view_serializer == view_serializer


# Test error() method


class TestInterceptorFactoryError:
    """Tests for InterceptorFactory.error() method."""

    @pytest.fixture
    def factory_with_errors(self) -> InterceptorFactory:
        """Create factory with predefined errors map."""
        return InterceptorFactory(errors_map={400: SampleError400, 404: SampleError404, 500: SampleError500})

    def test_error_returns_interceptor(self, factory_with_errors: InterceptorFactory) -> None:
        """Test that error() returns an Interceptor instance."""
        interceptor = factory_with_errors.error(400)
        assert isinstance(interceptor, Interceptor)

    def test_error_sets_correct_catch_type(self, factory_with_errors: InterceptorFactory) -> None:
        """Test that error() sets correct catch type from errors map."""
        interceptor = factory_with_errors.error(400)
        assert interceptor.get_desired_type() == SampleError400

        interceptor_404 = factory_with_errors.error(404)
        assert interceptor_404.get_desired_type() == SampleError404

    def test_error_sets_correct_status_code(self, factory_with_errors: InterceptorFactory) -> None:
        """Test that error() sets correct status code."""
        interceptor = factory_with_errors.error(400)
        assert interceptor.get_status_code() == 400

        interceptor_500 = factory_with_errors.error(500)
        assert interceptor_500.get_status_code() == 500

    def test_error_sets_error_response_model(self, factory_with_errors: InterceptorFactory) -> None:
        """Test that error() sets ErrorResponseModel as response model."""
        interceptor = factory_with_errors.error(400)
        assert interceptor.get_response_model() == ErrorResponseModel

    def test_error_uses_default_response_class(self) -> None:
        """Test that error() uses default response class when not specified."""
        factory = InterceptorFactory(
            errors_map={400: SampleError400},
            default_response_class=JSONResponse,
        )
        interceptor = factory.error(400)
        assert interceptor._response_type == JSONResponse

    def test_error_uses_custom_response_class(self, factory_with_errors: InterceptorFactory) -> None:
        """Test that error() uses custom response class when specified."""
        interceptor = factory_with_errors.error(400, response_class=JSONResponse)
        assert interceptor._response_type == JSONResponse

    def test_error_uses_default_serializer(self) -> None:
        """Test that error() uses default error serializer when not specified."""
        error_serializer = Mock()
        factory = InterceptorFactory(
            errors_map={400: SampleError400},
            default_error_serializer=error_serializer,
        )
        interceptor = factory.error(400)
        # Check that the serializer is a ResponseMapping with the provided serializer
        assert isinstance(interceptor._serializer, ResponseMapping)

    def test_error_uses_custom_serializer(self, factory_with_errors: InterceptorFactory) -> None:
        """Test that error() uses custom serializer when specified."""
        custom_serializer = Mock()
        interceptor = factory_with_errors.error(400, serializer=custom_serializer)
        assert isinstance(interceptor._serializer, ResponseMapping)


# Test event() method


class TestInterceptorFactoryEvent:
    """Tests for InterceptorFactory.event() method."""

    @pytest.fixture
    def factory(self) -> InterceptorFactory:
        """Create basic factory."""
        return InterceptorFactory()

    def test_event_returns_interceptor(self, factory: InterceptorFactory) -> None:
        """Test that event() returns an Interceptor instance."""
        interceptor = factory.event(SampleEvent, SampleResponseData)
        assert isinstance(interceptor, Interceptor)

    def test_event_sets_correct_catch_type(self, factory: InterceptorFactory) -> None:
        """Test that event() sets correct catch type."""
        interceptor = factory.event(SampleEvent, SampleResponseData)
        assert interceptor.get_desired_type() == SampleEvent

    def test_event_sets_status_code_200(self, factory: InterceptorFactory) -> None:
        """Test that event() sets status code to 200."""
        interceptor = factory.event(SampleEvent, SampleResponseData)
        assert interceptor.get_status_code() == 200

    def test_event_creates_response_model(self, factory: InterceptorFactory) -> None:
        """Test that event() creates a response model from response_data."""
        interceptor = factory.event(SampleEvent, SampleResponseData)
        model = interceptor.get_response_model()
        assert model is not None
        # Check that the model name includes the response data name
        assert "SampleResponseData" in model.__name__

    def test_event_uses_default_response_class(self) -> None:
        """Test that event() uses default response class when not specified."""
        factory = InterceptorFactory(default_response_class=JSONResponse)
        interceptor = factory.event(SampleEvent, SampleResponseData)
        assert interceptor._response_type == JSONResponse

    def test_event_uses_custom_response_class(self, factory: InterceptorFactory) -> None:
        """Test that event() uses custom response class when specified."""
        interceptor = factory.event(SampleEvent, SampleResponseData, response_class=JSONResponse)
        assert interceptor._response_type == JSONResponse

    def test_event_uses_default_serializer(self) -> None:
        """Test that event() uses default event serializer when not specified."""
        event_serializer = Mock()
        factory = InterceptorFactory(default_event_serializer=event_serializer)
        interceptor = factory.event(SampleEvent, SampleResponseData)
        assert isinstance(interceptor._serializer, ResponseMapping)

    def test_event_uses_custom_serializer(self, factory: InterceptorFactory) -> None:
        """Test that event() uses custom serializer when specified."""
        custom_serializer = Mock()
        interceptor = factory.event(SampleEvent, SampleResponseData, serializer=custom_serializer)
        assert isinstance(interceptor._serializer, ResponseMapping)


# Test list_view() method


class TestInterceptorFactoryListView:
    """Tests for InterceptorFactory.list_view() method."""

    @pytest.fixture
    def factory(self) -> InterceptorFactory:
        """Create basic factory."""
        return InterceptorFactory()

    def test_list_view_returns_interceptor(self, factory: InterceptorFactory) -> None:
        """Test that list_view() returns an Interceptor instance."""
        interceptor = factory.list_view(SampleResponseData)
        assert isinstance(interceptor, Interceptor)

    def test_list_view_sets_view_as_catch_type(self, factory: InterceptorFactory) -> None:
        """Test that list_view() sets View as catch type."""
        interceptor = factory.list_view(SampleResponseData)
        assert interceptor.get_desired_type() == View

    def test_list_view_sets_status_code_200(self, factory: InterceptorFactory) -> None:
        """Test that list_view() sets status code to 200."""
        interceptor = factory.list_view(SampleResponseData)
        assert interceptor.get_status_code() == 200

    def test_list_view_creates_list_response_model(self, factory: InterceptorFactory) -> None:
        """Test that list_view() creates a list response model."""
        interceptor = factory.list_view(SampleResponseData)
        model = interceptor.get_response_model()
        assert model is not None
        # The model should be created for a list type
        assert "list" in model.__name__

    def test_list_view_uses_default_response_class(self) -> None:
        """Test that list_view() uses default response class when not specified."""
        factory = InterceptorFactory(default_response_class=JSONResponse)
        interceptor = factory.list_view(SampleResponseData)
        assert interceptor._response_type == JSONResponse

    def test_list_view_uses_custom_response_class(self, factory: InterceptorFactory) -> None:
        """Test that list_view() uses custom response class when specified."""
        interceptor = factory.list_view(SampleResponseData, response_class=JSONResponse)
        assert interceptor._response_type == JSONResponse

    def test_list_view_uses_view_mapping_serializer(self, factory: InterceptorFactory) -> None:
        """Test that list_view() uses ViewMapping as serializer."""
        interceptor = factory.list_view(SampleResponseData)
        assert isinstance(interceptor._serializer, ViewMapping)

    def test_list_view_uses_default_serializer(self) -> None:
        """Test that list_view() uses default view serializer when not specified."""
        view_serializer = Mock()
        factory = InterceptorFactory(default_view_serializer=view_serializer)
        interceptor = factory.list_view(SampleResponseData)
        assert isinstance(interceptor._serializer, ViewMapping)

    def test_list_view_uses_custom_serializer(self, factory: InterceptorFactory) -> None:
        """Test that list_view() uses custom serializer when specified."""
        custom_serializer = Mock()
        interceptor = factory.list_view(SampleResponseData, serializer=custom_serializer)
        assert isinstance(interceptor._serializer, ViewMapping)


# Test item_view() method


class TestInterceptorFactoryItemView:
    """Tests for InterceptorFactory.item_view() method."""

    @pytest.fixture
    def factory(self) -> InterceptorFactory:
        """Create basic factory."""
        return InterceptorFactory()

    def test_item_view_returns_interceptor(self, factory: InterceptorFactory) -> None:
        """Test that item_view() returns an Interceptor instance."""
        interceptor = factory.item_view(SampleResponseData)
        assert isinstance(interceptor, Interceptor)

    def test_item_view_sets_view_as_catch_type(self, factory: InterceptorFactory) -> None:
        """Test that item_view() sets View as catch type."""
        interceptor = factory.item_view(SampleResponseData)
        assert interceptor.get_desired_type() == View

    def test_item_view_sets_status_code_200(self, factory: InterceptorFactory) -> None:
        """Test that item_view() sets status code to 200."""
        interceptor = factory.item_view(SampleResponseData)
        assert interceptor.get_status_code() == 200

    def test_item_view_creates_item_response_model(self, factory: InterceptorFactory) -> None:
        """Test that item_view() creates an item response model."""
        interceptor = factory.item_view(SampleResponseData)
        model = interceptor.get_response_model()
        assert model is not None
        assert "SampleResponseData" in model.__name__

    def test_item_view_uses_default_response_class(self) -> None:
        """Test that item_view() uses default response class when not specified."""
        factory = InterceptorFactory(default_response_class=JSONResponse)
        interceptor = factory.item_view(SampleResponseData)
        assert interceptor._response_type == JSONResponse

    def test_item_view_uses_custom_response_class(self, factory: InterceptorFactory) -> None:
        """Test that item_view() uses custom response class when specified."""
        interceptor = factory.item_view(SampleResponseData, response_class=JSONResponse)
        assert interceptor._response_type == JSONResponse

    def test_item_view_uses_view_mapping_serializer(self, factory: InterceptorFactory) -> None:
        """Test that item_view() uses ViewMapping as serializer."""
        interceptor = factory.item_view(SampleResponseData)
        assert isinstance(interceptor._serializer, ViewMapping)

    def test_item_view_uses_default_serializer(self) -> None:
        """Test that item_view() uses default view serializer when not specified."""
        view_serializer = Mock()
        factory = InterceptorFactory(default_view_serializer=view_serializer)
        interceptor = factory.item_view(SampleResponseData)
        assert isinstance(interceptor._serializer, ViewMapping)

    def test_item_view_uses_custom_serializer(self, factory: InterceptorFactory) -> None:
        """Test that item_view() uses custom serializer when specified."""
        custom_serializer = Mock()
        interceptor = factory.item_view(SampleResponseData, serializer=custom_serializer)
        assert isinstance(interceptor._serializer, ViewMapping)


# Integration tests


class TestInterceptorFactoryIntegration:
    """Integration tests for InterceptorFactory."""

    def test_factory_with_all_options(self) -> None:
        """Test factory with all configuration options."""
        event_serializer = lambda msg: {"event": str(msg)}
        error_serializer = lambda err: {"error": str(err)}
        view_serializer = lambda view: view

        factory = InterceptorFactory(
            errors_map={400: SampleError400, 404: SampleError404},
            default_response_class=JSONResponse,
            default_event_serializer=event_serializer,
            default_error_serializer=error_serializer,
            default_view_serializer=view_serializer,
        )

        # Test error interceptor
        error_interceptor = factory.error(400)
        assert error_interceptor.get_desired_type() == SampleError400
        assert error_interceptor.get_status_code() == 400
        assert error_interceptor._response_type == JSONResponse

        # Test event interceptor
        event_interceptor = factory.event(SampleEvent, SampleResponseData)
        assert event_interceptor.get_desired_type() == SampleEvent
        assert event_interceptor.get_status_code() == 200
        assert event_interceptor._response_type == JSONResponse

        # Test list_view interceptor
        list_interceptor = factory.list_view(SampleResponseData)
        assert list_interceptor.get_desired_type() == View
        assert list_interceptor.get_status_code() == 200
        assert list_interceptor._response_type == JSONResponse

        # Test item_view interceptor
        item_interceptor = factory.item_view(SampleResponseData)
        assert item_interceptor.get_desired_type() == View
        assert item_interceptor.get_status_code() == 200
        assert item_interceptor._response_type == JSONResponse

    def test_multiple_interceptors_from_same_factory(self) -> None:
        """Test creating multiple interceptors from the same factory."""
        factory = InterceptorFactory(errors_map={400: SampleError400, 404: SampleError404, 500: SampleError500})

        interceptors = [
            factory.error(400),
            factory.error(404),
            factory.error(500),
            factory.event(SampleEvent, SampleResponseData),
            factory.list_view(SampleResponseData),
            factory.item_view(SampleItemResponseData),
        ]

        # All should be Interceptor instances
        for interceptor in interceptors:
            assert isinstance(interceptor, Interceptor)

        # Each error interceptor should have different catch types
        assert interceptors[0].get_desired_type() == SampleError400
        assert interceptors[1].get_desired_type() == SampleError404
        assert interceptors[2].get_desired_type() == SampleError500
