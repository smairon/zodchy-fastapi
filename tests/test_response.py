import json
from collections.abc import AsyncIterator
from typing import Any, Callable, cast

import pytest
from fastapi.responses import JSONResponse, Response

from zodchy.codex.cqea import Error, Message
from zodchy_fastapi.definition.schema.response import ErrorResponseModel, ResponseModel
from zodchy_fastapi.response import ErrorInterceptor, Interceptor, ResponseDescriber
from zodchy_fastapi.routing import Batch


class PayloadMessage(Message):
    def __init__(self, value: int) -> None:
        self.value = value


class PayloadError(Error):
    def __init__(self, code: int) -> None:
        self.code = code


class DummyStream:
    def __init__(self, *messages: Message) -> None:
        self._messages = list(messages)

    def __aiter__(self) -> AsyncIterator[Message]:
        async def iterator() -> AsyncIterator[Message]:
            for message in self._messages:
                yield message

        return iterator()


def serializer_factory(recorder: list[tuple[Message, ...]]) -> Callable[..., dict[str, Any]]:
    def serializer(*messages: Message | Error) -> dict[str, Any]:
        recorder.append(messages)
        return {"values": [getattr(message, "value", None) for message in messages]}

    return serializer


def test_interceptor_without_serializer_returns_empty_response() -> None:
    interceptor = Interceptor(catch=PayloadMessage)
    response = interceptor(PayloadMessage(1))

    assert isinstance(response, Response)
    assert response.status_code == 204
    assert response.body == b""


def test_interceptor_with_serializer_builds_custom_response() -> None:
    recorded: list[tuple[Message, ...]] = []
    interceptor = Interceptor(
        catch=PayloadMessage,
        declare=(202, ResponseModel),
        response=(JSONResponse, serializer_factory(recorded)),
    )

    response = interceptor(PayloadMessage(1), PayloadMessage(2))

    assert response.status_code == 202
    assert json.loads(response.body) == {"values": [1, 2]}
    assert isinstance(recorded[0][0], PayloadMessage)
    assert recorded[0][0].value == 1


def test_error_interceptor_uses_mapping_for_status_code() -> None:
    recorded: list[tuple[Message, ...]] = []
    interceptor = ErrorInterceptor(
        mapping={PayloadError: 422},
        response=(JSONResponse, serializer_factory(recorded)),
    )

    response = interceptor(PayloadError(10))

    assert response.status_code == 422
    assert json.loads(response.body)["values"] == [None]
    assert interceptor.get_response_model() is ErrorResponseModel


def test_error_interceptor_defaults_to_internal_error_code() -> None:
    recorded: list[tuple[Message, ...]] = []
    interceptor = ErrorInterceptor(
        mapping={},
        response=(JSONResponse, serializer_factory(recorded)),
    )

    response = interceptor(PayloadError(11))

    assert response.status_code == 500


def test_batch_accumulates_type_information() -> None:
    batch = Batch(PayloadMessage(1))
    batch.append(PayloadMessage(2))

    assert batch.message_type is PayloadMessage
    batch_messages = list(batch)
    assert all(isinstance(msg, PayloadMessage) for msg in batch_messages)
    payload_values = [cast(PayloadMessage, msg).value for msg in batch_messages]
    assert payload_values == [1, 2]


def test_response_describer_iteration_exposes_interceptor_declarations() -> None:
    interceptor_one = Interceptor(PayloadMessage, declare=(205, ResponseModel))
    interceptor_two = Interceptor(PayloadMessage, declare=206)
    describer = ResponseDescriber(interceptor_one, interceptor_two)

    assert list(describer.get_schema()) == [(205, ResponseModel), (206, None)]


def test_response_describer_returns_interceptors() -> None:
    recorded: list[tuple[Message, ...]] = []
    interceptor = Interceptor(
        catch=PayloadMessage,
        declare=(207, ResponseModel),
        response=(JSONResponse, serializer_factory(recorded)),
    )
    describer = ResponseDescriber(interceptor)

    interceptors = list(describer.get_interceptors())
    assert len(interceptors) == 1
    assert interceptors[0] is interceptor


def test_interceptor_handles_messages_correctly() -> None:
    recorded: list[tuple[Message, ...]] = []
    interceptor = Interceptor(
        catch=PayloadMessage,
        declare=(207, ResponseModel),
        response=(JSONResponse, serializer_factory(recorded)),
    )

    response = interceptor(PayloadMessage(1), PayloadMessage(2))

    assert response is not None
    assert response.status_code == 207
    assert json.loads(response.body)["values"] == [1, 2]
    assert recorded
    assert isinstance(recorded[0][0], PayloadMessage)
    assert recorded[0][0].value == 1
