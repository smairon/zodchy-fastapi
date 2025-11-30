from collections.abc import Callable
from typing import Any

import pytest

from zodchy.codex.cqea import Message
from zodchy_fastapi.serializing import ResponseMapping, Serializer


class PayloadMessage(Message):
    def __init__(self, payload: Any) -> None:
        self.payload = payload


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
