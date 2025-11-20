import json
from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError

from zodchy_fastapi.middleware import JsonExceptionHandler


def _make_request() -> Request:
    return Request({"type": "http", "method": "GET", "path": "/", "headers": []})


def test_json_exception_handler_default_response_contains_details() -> None:
    handler = JsonExceptionHandler()
    exc = RuntimeError("boom")

    response = handler.default_exception_handler(_make_request(), exc)

    assert response.status_code == 500
    payload = json.loads(response.body)
    assert payload == {
        "code": 500,
        "message": "boom",
        "details": {"type": "RuntimeError"},
    }


def test_json_exception_handler_validation_response_aggregates_errors() -> None:
    handler = JsonExceptionHandler()
    errors = [
        {"loc": ("body", "name"), "msg": "Missing", "type": "value_error", "input": None},
        {"loc": ("query", "filters", "value"), "msg": "Invalid", "type": "value_error", "input": None},
    ]
    exc = RequestValidationError(errors)

    response = handler.validation_exception_handler(_make_request(), exc)

    assert response.status_code == 422
    payload = json.loads(response.body)
    assert payload["code"] == 422
    assert payload["message"] == "Validation Error"
    assert payload["details"] == {
        "body": {"name": "Missing"},
        "query": {"filters": {"value": "Invalid"}},
    }


def test_helper_methods_build_nested_data_correctly() -> None:
    handler = JsonExceptionHandler()

    nested = handler._nestify(("body", "items", "name"), "bad")
    merged = handler._merge({"body": {"items": {"index": 1}}}, nested)
    payload = handler._build_data(code=400, message="msg", details=merged)

    assert nested == {"body": {"items": {"name": "bad"}}}
    assert merged == {"body": {"items": {"name": "bad"}}}
    assert payload == {
        "code": 400,
        "message": "msg",
        "details": {"body": {"items": {"name": "bad"}}},
    }


def test_build_data_defaults_to_empty_details() -> None:
    handler = JsonExceptionHandler()

    payload = handler._build_data(200, "ok")

    assert payload == {"code": 200, "message": "ok", "details": {}}
