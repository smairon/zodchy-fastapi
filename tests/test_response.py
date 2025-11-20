import json
from collections.abc import AsyncIterator
from typing import Any, Callable, cast

import pytest
from fastapi.responses import JSONResponse, Response

from zodchy.codex.cqea import Error, Message
from zodchy_fastapi.definition.schema.response import ErrorResponseModel, ResponseModel
from zodchy_fastapi.response import Batch, DeclarativeAdapter, ErrorInterceptor, Interceptor


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
    assert interceptor.response_model is ErrorResponseModel


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


def test_declarative_adapter_iteration_exposes_interceptor_declarations() -> None:
    interceptor_one = Interceptor(PayloadMessage, declare=(205, ResponseModel))
    interceptor_two = Interceptor(PayloadMessage, declare=206)
    adapter = DeclarativeAdapter(interceptor_one, interceptor_two)

    assert list(adapter) == [(205, ResponseModel), (206, None)]


@pytest.mark.asyncio
async def test_declarative_adapter_processes_stream_and_returns_response() -> None:
    recorded: list[tuple[Message, ...]] = []
    interceptor = Interceptor(
        catch=PayloadMessage,
        declare=(207, ResponseModel),
        response=(JSONResponse, serializer_factory(recorded)),
    )
    adapter = DeclarativeAdapter(interceptor)

    response = await adapter(DummyStream(PayloadMessage(1), PayloadMessage(2)))

    assert response is not None
    assert response.status_code == 207
    assert json.loads(response.body)["values"] == [1]
    assert recorded
    assert isinstance(recorded[0][0], PayloadMessage)
    assert recorded[0][0].value == 1


@pytest.mark.asyncio
async def test_declarative_adapter_returns_none_when_no_interceptor_matches() -> None:
    other_interceptor = Interceptor(catch=PayloadError)
    adapter = DeclarativeAdapter(other_interceptor)

    response = await adapter(DummyStream(PayloadMessage(1)))

    assert response is None


@pytest.mark.asyncio
async def test_group_stream_yields_all_batches() -> None:
    interceptor = Interceptor(PayloadMessage)
    adapter = DeclarativeAdapter(interceptor)
    stream = DummyStream(PayloadMessage(1), PayloadMessage(2))

    batches = [batch async for batch in adapter._group_stream(stream)]

    assert len(batches) == 2
    batch_values = []
    for batch in batches:
        payload_batch = []
        for msg in batch:
            payload_batch.append(cast(PayloadMessage, msg).value)
        batch_values.append(payload_batch)
    assert batch_values == [[1], [2]]