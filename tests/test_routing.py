import inspect
from collections.abc import AsyncIterator, Generator
from typing import Any, Awaitable, cast

import pytest
from fastapi import APIRouter, Response

from zodchy.codex.cqea import Message
from zodchy_fastapi.definition.contracts import EndpointContract, RouteContract
from zodchy_fastapi.definition.schema.response import ResponseModel
from zodchy_fastapi.routing import Endpoint, Route, Router
from zodchy.toolbox.processing import AsyncMessageStreamContract


class DummyTask(Message):
    def __init__(self, identifier: int) -> None:
        self.identifier = identifier


class FakeRequestAdapter:
    def __init__(self) -> None:
        self.received_kwargs: dict[str, Any] | None = None

    def route_params(self) -> dict[str, type]:
        return {"item_id": int}

    def __call__(self, **kwargs: Any) -> list[Message]:
        self.received_kwargs = kwargs
        return [DummyTask(kwargs.get("item_id", 0))]


class FakeStream:
    def __init__(self, messages: list[Message]) -> None:
        self._messages = messages

    def __aiter__(self) -> AsyncIterator[Message]:
        async def iterator() -> AsyncIterator[Message]:
            for message in self._messages:
                yield message

        return iterator()


class FakePipeline:
    def __init__(self) -> None:
        self.captured_messages: tuple[Message, ...] | None = None

    async def __call__(self, *messages: Message, **_: Any) -> AsyncMessageStreamContract:
        self.captured_messages = messages
        return FakeStream(list(messages))


class FakeResponseAdapter:
    def __init__(self) -> None:
        self.streams: list[AsyncMessageStreamContract] = []

    def __call__(self, stream: AsyncMessageStreamContract) -> Response | None:
        self.streams.append(stream)
        return Response(status_code=201)

    def __iter__(self) -> Generator[tuple[int, type[ResponseModel]], None, None]:
        yield (200, ResponseModel)


def _build_endpoint() -> tuple[Endpoint, FakeRequestAdapter, FakeResponseAdapter, FakePipeline]:
    request_adapter = FakeRequestAdapter()
    response_adapter = FakeResponseAdapter()
    pipeline = FakePipeline()
    return Endpoint(request_adapter, response_adapter, pipeline), request_adapter, response_adapter, pipeline


def test_route_exposes_core_properties_and_responses() -> None:
    endpoint, _, response_adapter, _ = _build_endpoint()
    endpoint_contract = cast(EndpointContract, endpoint)
    route = Route(
        path="/items",
        methods=["GET"],
        tags=["items"],
        endpoint=endpoint_contract,
        dependencies=[],
    )

    assert route.path == "/items"
    assert route.methods == ["GET"]
    assert route.tags == ["items"]
    assert route.endpoint is endpoint_contract
    assert route.params == {"dependencies": []}
    assert route.responses == {200: {"model": ResponseModel}}
    assert list(route.endpoint.response_adapter) == [(200, ResponseModel)]


def test_router_registers_routes_on_fastapi_router() -> None:
    endpoint, _, _, _ = _build_endpoint()
    endpoint_contract = cast(EndpointContract, endpoint)
    route = Route("/items", ["GET"], ["items"], endpoint_contract)
    router = APIRouter()
    custom_router = Router(router)

    result = custom_router([cast(RouteContract, route)])

    assert result is router
    assert any(getattr(r, "path", None) == "/items" for r in router.routes)

@pytest.mark.asyncio
async def test_endpoint_callable_runs_pipeline_and_response_adapter() -> None:
    endpoint, request_adapter, response_adapter, pipeline = _build_endpoint()
    handler = endpoint()

    signature = inspect.signature(handler)
    assert "item_id" in signature.parameters
    assert signature.return_annotation is ResponseModel

    callable_handler = cast(Awaitable[Response], handler(item_id=7))
    response = await callable_handler

    assert isinstance(response, Response)
    assert response.status_code == 201
    assert request_adapter.received_kwargs == {"item_id": 7}
    assert pipeline.captured_messages is not None
    assert isinstance(pipeline.captured_messages[0], DummyTask)
    assert response_adapter.streams