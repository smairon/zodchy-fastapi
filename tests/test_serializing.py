from collections.abc import Callable
from typing import Any

import pytest

from zodchy.codex.cqea import Message, View
from zodchy_fastapi.serializing import ResponseMapping, Serializer, ViewMapping


class PayloadMessage(Message):
    def __init__(self, payload: Any) -> None:
        self.payload = payload


class SampleView(View):
    def __init__(self, data: Any, meta: dict[str, Any] | None = None) -> None:
        self._data = data
        self._meta = meta

    def data(self) -> Any:
        return self._data

    def meta(self) -> dict[str, Any] | None:
        return self._meta


def recorder_serializer(recorder: list[Any]) -> Callable[[Message], Any]:
    def _serialize(message: Message) -> Any:
        recorder.append(message)
        return getattr(message, "payload", None)

    return _serialize


def test_response_mapping_returns_single_payload_without_list_wrapper() -> None:
    recorded: list[Message] = []
    serializer = ResponseMapping(message_serializer=recorder_serializer(recorded))
    message = PayloadMessage({"value": 10})

    response = serializer(message)

    assert response == {"data": {"value": 10}}
    assert recorded == [message]


def test_response_mapping_handles_multiple_messages() -> None:
    recorded: list[Message] = []
    serializer = ResponseMapping(message_serializer=recorder_serializer(recorded))
    first = PayloadMessage(1)
    second = PayloadMessage(2)

    response = serializer(first, second)

    assert response == {"data": [1, 2]}
    assert recorded == [first, second]


class ProxySerializer(Serializer):
    def __call__(self, *messages: Message) -> Any:  # pragma: no cover - exercised via base
        raise NotImplementedError("__call__ must be implemented by subclasses")


def test_serializer_base_call_raises_not_implemented() -> None:
    proxy = ProxySerializer(lambda message: message)
    with pytest.raises(NotImplementedError):
        proxy(PayloadMessage("unused"))


# ViewMapping tests


def test_view_mapping_returns_empty_data_for_no_messages() -> None:
    serializer = ViewMapping()

    response = serializer()

    assert response == {"data": []}


def test_view_mapping_returns_data_without_meta() -> None:
    serializer = ViewMapping()
    view = SampleView(data=[{"id": 1}, {"id": 2}])

    response = serializer(view)

    assert response == {"data": [{"id": 1}, {"id": 2}]}


def test_view_mapping_returns_data_with_meta() -> None:
    serializer = ViewMapping()
    view = SampleView(
        data=[{"id": 1}],
        meta={"total": 100, "page": 1},
    )

    response = serializer(view)

    assert response == {
        "data": [{"id": 1}],
        "meta": {"total": 100, "page": 1},
    }


def test_view_mapping_uses_message_serializer_on_data() -> None:
    def transform(data: Any) -> Any:
        return [{"transformed": item["id"]} for item in data]

    serializer = ViewMapping(message_serializer=transform)
    view = SampleView(data=[{"id": 1}, {"id": 2}])

    response = serializer(view)

    assert response == {"data": [{"transformed": 1}, {"transformed": 2}]}


def test_view_mapping_uses_message_serializer_with_meta() -> None:
    def transform(data: Any) -> Any:
        return {"count": len(data)}

    serializer = ViewMapping(message_serializer=transform)
    view = SampleView(
        data=[1, 2, 3],
        meta={"cursor": "abc123"},
    )

    response = serializer(view)

    assert response == {
        "data": {"count": 3},
        "meta": {"cursor": "abc123"},
    }


# ResponseMapping additional tests


def test_response_mapping_without_serializer_returns_message_directly() -> None:
    serializer = ResponseMapping()
    message = PayloadMessage({"value": 42})

    response = serializer(message)

    assert response == {"data": message}


def test_response_mapping_without_serializer_multiple_messages() -> None:
    serializer = ResponseMapping()
    first = PayloadMessage(1)
    second = PayloadMessage(2)

    response = serializer(first, second)

    assert response == {"data": [first, second]}
