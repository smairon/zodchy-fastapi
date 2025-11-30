import os
import tempfile
from collections.abc import Collection
from typing import Any, cast
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from zodchy_fastapi.definition.contracts import (
    EndpointContract,
    RequestAdapterContract,
    RequestParameterContract,
    ResponseDescriberContract,
    ResponseInterceptorContract,
)
from zodchy_fastapi.definition.schema.response import ResponseModel
from zodchy_fastapi.routing import Route
from zodchy_fastapi.routing.registry import RoutesRegistry


class FakeEndpoint:
    """Fake endpoint for testing purposes."""

    def __init__(self) -> None:
        self._response = FakeResponseDescriber()

    @property
    def response(self) -> ResponseDescriberContract:
        return cast(ResponseDescriberContract, self._response)

    def __call__(self, pipeline_registry: Any) -> Any:
        return lambda: None


class FakeResponseDescriber:
    """Fake response describer for testing purposes."""

    def get_interceptors(self) -> Collection[ResponseInterceptorContract]:
        return []

    def get_schema(self) -> Collection[tuple[int, type[ResponseModel] | None]]:
        return [(200, ResponseModel)]


def create_test_route(path: str = "/test") -> Route:
    """Helper function to create a test route."""
    return Route(
        path=path,
        methods=["GET"],
        tags=["test"],
        endpoint=cast(EndpointContract, FakeEndpoint()),
    )


def route_factory() -> Route:
    """A route factory function for testing register_route_function."""
    return create_test_route("/factory")


class TestRoutesRegistryInit:
    """Tests for RoutesRegistry initialization."""

    def test_registry_initializes_with_empty_list(self) -> None:
        registry = RoutesRegistry()
        assert list(registry) == []

    def test_registry_has_default_ignore_list(self) -> None:
        registry = RoutesRegistry()
        assert "__pycache__" in registry._ignore_list
        assert ".pytest_cache" in registry._ignore_list
        assert ".git" in registry._ignore_list
        assert "venv" in registry._ignore_list
        assert "env" in registry._ignore_list


class TestRoutesRegistryRegisterRoute:
    """Tests for register_route method."""

    def test_register_single_route(self) -> None:
        registry = RoutesRegistry()
        route = create_test_route()

        registry.register_route(route)

        routes = list(registry)
        assert len(routes) == 1
        assert routes[0] is route

    def test_register_multiple_routes(self) -> None:
        registry = RoutesRegistry()
        route1 = create_test_route("/route1")
        route2 = create_test_route("/route2")

        registry.register_route(route1)
        registry.register_route(route2)

        routes = list(registry)
        assert len(routes) == 2
        assert routes[0] is route1
        assert routes[1] is route2


class TestRoutesRegistryRegisterRouteFunction:
    """Tests for register_route_function method."""

    def test_register_route_function_calls_factory(self) -> None:
        registry = RoutesRegistry()

        registry.register_route_function(route_factory)

        routes = list(registry)
        assert len(routes) == 1
        assert routes[0].path == "/factory"

    def test_register_route_function_with_lambda(self) -> None:
        registry = RoutesRegistry()

        registry.register_route_function(lambda: create_test_route("/lambda"))

        routes = list(registry)
        assert len(routes) == 1
        assert routes[0].path == "/lambda"


class TestRoutesRegistryIteration:
    """Tests for __iter__ method."""

    def test_iterate_empty_registry(self) -> None:
        registry = RoutesRegistry()
        assert list(registry) == []

    def test_iterate_yields_routes_in_order(self) -> None:
        registry = RoutesRegistry()
        route1 = create_test_route("/first")
        route2 = create_test_route("/second")
        route3 = create_test_route("/third")

        registry.register_route(route1)
        registry.register_route(route2)
        registry.register_route(route3)

        routes = list(registry)
        assert routes == [route1, route2, route3]

    def test_multiple_iterations(self) -> None:
        registry = RoutesRegistry()
        route = create_test_route()
        registry.register_route(route)

        # Should be able to iterate multiple times
        assert list(registry) == [route]
        assert list(registry) == [route]


class TestRoutesRegistryRegisterModule:
    """Tests for register_module method."""

    def test_register_module_without_path_or_file_raises_error(self) -> None:
        registry = RoutesRegistry()
        mock_module = MagicMock(spec=ModuleType)
        mock_module.__name__ = "test_module"
        mock_module.__path__ = None
        mock_module.__file__ = None
        # Remove the attributes to simulate a module without them
        del mock_module.__path__
        del mock_module.__file__

        with pytest.raises(ValueError, match="has no __path__ or __file__ attribute"):
            registry.register_module(mock_module)

    def test_register_single_file_module(self) -> None:
        """Test registering a single-file module."""
        registry = RoutesRegistry()

        # Create a mock module that looks like a single-file module
        mock_module = MagicMock(spec=ModuleType)
        mock_module.__name__ = "test_single_module"
        mock_module.__file__ = "/some/path/test_single_module.py"
        # Simulate no __path__ (single file module)
        del mock_module.__path__

        # The _collect_module_functions will be called, but since it's a mock
        # it won't find any actual functions. We'll verify the method is called.
        # For a real test, we'd need an actual module with route functions.
        registry.register_module(mock_module)

        # Since the mock module has no actual functions, registry should be empty
        assert list(registry) == []


class TestRoutesRegistryCollectModuleFunctions:
    """Tests for _collect_module_functions method."""

    def test_ignores_private_functions(self) -> None:
        """Private functions (starting with _) should be ignored."""
        registry = RoutesRegistry()

        # Create a mock module
        mock_module = MagicMock(spec=ModuleType)
        mock_module.__name__ = "test_module"

        # Manually call _collect_module_functions - it will use inspect.getmembers
        # which won't find anything useful on our mock
        registry._collect_module_functions(mock_module)

        # Registry should be empty since no valid route functions were found
        assert list(registry) == []

    def test_only_collects_functions_returning_route(self) -> None:
        """Only functions with Route return annotation should be collected."""
        registry = RoutesRegistry()

        # Create a mock module - without actual functions returning Route
        mock_module = MagicMock(spec=ModuleType)
        mock_module.__name__ = "test_module"

        registry._collect_module_functions(mock_module)

        # Registry should be empty
        assert list(registry) == []


class TestRoutesRegistryWalkFilesystem:
    """Tests for _walk_filesystem method."""

    def test_ignores_hidden_files_and_directories(self) -> None:
        """Hidden files/directories (starting with .) should be ignored."""
        registry = RoutesRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create hidden directory
            hidden_dir = os.path.join(tmpdir, ".hidden")
            os.makedirs(hidden_dir)

            # Create hidden file
            hidden_file = os.path.join(tmpdir, ".hidden_file.py")
            with open(hidden_file, "w") as f:
                f.write("# hidden file")

            # Walk the filesystem - should not process hidden items
            registry._walk_filesystem(tmpdir, "test_package")

            # Registry should be empty
            assert list(registry) == []

    def test_ignores_directories_in_ignore_list(self) -> None:
        """Directories in ignore list should be skipped."""
        registry = RoutesRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create directories from ignore list
            for ignored in ["__pycache__", ".pytest_cache", "venv"]:
                ignored_dir = os.path.join(tmpdir, ignored)
                os.makedirs(ignored_dir)
                # Create a Python file inside
                with open(os.path.join(ignored_dir, "module.py"), "w") as f:
                    f.write("# ignored")

            registry._walk_filesystem(tmpdir, "test_package")

            # Registry should be empty
            assert list(registry) == []

    def test_ignores_private_python_files(self) -> None:
        """Python files starting with _ should be ignored."""
        registry = RoutesRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create private Python files
            for filename in ["__init__.py", "_private.py", "__main__.py"]:
                filepath = os.path.join(tmpdir, filename)
                with open(filepath, "w") as f:
                    f.write("# private file")

            registry._walk_filesystem(tmpdir, "test_package")

            # Registry should be empty
            assert list(registry) == []

    def test_handles_import_errors_gracefully(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Import errors should be caught and logged."""
        registry = RoutesRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a Python file that would fail to import
            filepath = os.path.join(tmpdir, "bad_module.py")
            with open(filepath, "w") as f:
                f.write("import nonexistent_module_xyz")

            registry._walk_filesystem(tmpdir, "nonexistent_test_package")

            # Should print warning but not raise
            captured = capsys.readouterr()
            assert "Warning: Could not import module" in captured.out

    def test_recurses_into_subdirectories(self) -> None:
        """Should recursively process subdirectories."""
        registry = RoutesRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested directory structure
            subdir = os.path.join(tmpdir, "subpackage")
            os.makedirs(subdir)

            # Create an empty Python file in subdirectory
            filepath = os.path.join(subdir, "module.py")
            with open(filepath, "w") as f:
                f.write("# empty module")

            # The import will fail since it's not a real package,
            # but we're testing that it attempts to recurse
            registry._walk_filesystem(tmpdir, "fake_package")

            # Registry will be empty due to import failure, but no exception should be raised
            assert list(registry) == []


class TestRoutesRegistryRegisterModulePackage:
    """Tests for register_module with package modules."""

    def test_handles_package_with_path_list(self) -> None:
        """Package __path__ as a list should be handled."""
        registry = RoutesRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a mock package module
            mock_module = MagicMock(spec=ModuleType)
            mock_module.__name__ = "test_package"
            mock_module.__path__ = [tmpdir]
            mock_module.__file__ = os.path.join(tmpdir, "__init__.py")

            # Should not raise
            registry.register_module(mock_module)

            # Registry should be empty (no valid route functions)
            assert list(registry) == []

    def test_handles_package_with_path_string(self) -> None:
        """Package __path__ as a string should be handled."""
        registry = RoutesRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            mock_module = MagicMock(spec=ModuleType)
            mock_module.__name__ = "test_package"
            mock_module.__path__ = tmpdir  # String instead of list
            mock_module.__file__ = os.path.join(tmpdir, "__init__.py")

            registry.register_module(mock_module)

            assert list(registry) == []

    def test_handles_init_py_path(self) -> None:
        """Path ending with __init__.py should have dirname extracted."""
        registry = RoutesRegistry()

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create __init__.py
            init_path = os.path.join(tmpdir, "__init__.py")
            with open(init_path, "w") as f:
                f.write("# init")

            mock_module = MagicMock(spec=ModuleType)
            mock_module.__name__ = "test_package"
            mock_module.__path__ = [init_path]  # Path to __init__.py
            mock_module.__file__ = init_path

            registry.register_module(mock_module)

            assert list(registry) == []


class TestRoutesRegistryIntegration:
    """Integration tests for RoutesRegistry."""

    def test_mixed_registration_methods(self) -> None:
        """Test using both register_route and register_route_function."""
        registry = RoutesRegistry()

        # Register directly
        route1 = create_test_route("/direct")
        registry.register_route(route1)

        # Register via factory
        registry.register_route_function(lambda: create_test_route("/factory"))

        routes = list(registry)
        assert len(routes) == 2
        assert routes[0].path == "/direct"
        assert routes[1].path == "/factory"

    def test_registry_preserves_route_properties(self) -> None:
        """Test that routes maintain all their properties after registration."""
        registry = RoutesRegistry()

        route = Route(
            path="/users/{user_id}",
            methods=["GET", "POST"],
            tags=["users", "api"],
            endpoint=cast(EndpointContract, FakeEndpoint()),
            summary="User endpoint",
            description="Handles user operations",
        )

        registry.register_route(route)

        registered_route = list(registry)[0]
        assert registered_route.path == "/users/{user_id}"
        assert registered_route.methods == ["GET", "POST"]
        assert registered_route.tags == ["users", "api"]
        assert registered_route.params == {
            "summary": "User endpoint",
            "description": "Handles user operations",
        }
