import inspect
from collections.abc import AsyncIterator, Collection
from typing import Any, Awaitable, cast

import pytest
from fastapi import APIRouter, Response

from zodchy.codex.cqea import Message
from zodchy_fastapi.definition.contracts import (
    EndpointContract,
    RequestAdapterContract,
    RequestDescriberContract,
    RequestParameterContract,
    ResponseDescriberContract,
    ResponseInterceptorContract,
    RouteContract,
)
from zodchy_fastapi.definition.schema.response import ResponseModel
from zodchy_fastapi.routing import Batch, Endpoint, Route, Router


class DummyTask(Message):
    def __init__(self, identifier: int) -> None:
        self.identifier = identifier


class FakeParameter:
    def __init__(self, name: str, param_type: type) -> None:
        self._name = name
        self._type = param_type
        self._value: Any = None

    def get_name(self) -> str:
        return self._name

    def get_type(self) -> type:
        return self._type

    def set_value(self, value: Any) -> None:
        self._value = value

    def __call__(self) -> dict[str, Any]:
        return {self._name: self._value}


class FakeRequestAdapter:
    def __init__(self) -> None:
        self.received_kwargs: dict[str, Any] | None = None

    def __call__(self, **kwargs: Any) -> list[Message]:
        self.received_kwargs = kwargs
        item_id = 0
        for param in kwargs.values():
            if hasattr(param, "_value"):
                item_id = param._value
                break
            elif isinstance(param, int):
                item_id = param
                break
        return [DummyTask(item_id)]


class FakePipeline:
    def __init__(self) -> None:
        self.captured_messages: tuple[Message, ...] | None = None

    async def __call__(self, *messages: Message, **_: Any) -> AsyncIterator[Message]:
        self.captured_messages = messages
        for message in messages:
            yield message


class FakeInterceptor:
    def __init__(self) -> None:
        self.received_messages: list[Message] = []

    def get_status_code(self) -> int:
        return 201

    def get_desired_type(self) -> type[Message]:
        return DummyTask

    def get_response_model(self) -> type[ResponseModel]:
        return ResponseModel

    def __call__(self, *messages: Message) -> Response:
        self.received_messages.extend(messages)
        return Response(status_code=201)


class FakeRequestDescriber:
    def __init__(self, adapter: FakeRequestAdapter, parameters: list[FakeParameter]) -> None:
        self._adapter = adapter
        self._parameters = parameters

    def get_adapter(self) -> RequestAdapterContract:
        return self._adapter

    def get_schema(self) -> Collection[RequestParameterContract]:
        return cast(Collection[RequestParameterContract], self._parameters)


class FakeResponseDescriber:
    def __init__(self, interceptor: FakeInterceptor) -> None:
        self._interceptor = interceptor

    def get_interceptors(self) -> Collection[ResponseInterceptorContract]:
        return [cast(ResponseInterceptorContract, self._interceptor)]

    def get_schema(self) -> Collection[tuple[int, type[ResponseModel] | None]]:
        return [(200, ResponseModel)]


def _build_endpoint() -> (
    tuple[Endpoint, FakeRequestAdapter, FakeResponseDescriber, FakePipeline, FakeParameter, FakeInterceptor]
):
    request_adapter = FakeRequestAdapter()
    parameter = FakeParameter("item_id", int)
    request_describer = FakeRequestDescriber(request_adapter, [parameter])
    interceptor = FakeInterceptor()
    response_describer = FakeResponseDescriber(interceptor)
    pipeline = FakePipeline()
    return (
        Endpoint(
            cast(RequestDescriberContract, request_describer),
            cast(ResponseDescriberContract, response_describer),
            pipeline,
        ),
        request_adapter,
        response_describer,
        pipeline,
        parameter,
        interceptor,
    )


def test_route_exposes_core_properties_and_responses() -> None:
    endpoint, _, response_describer, _, _, _ = _build_endpoint()
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
    assert list(route.endpoint.response.get_schema()) == [(200, ResponseModel)]


def test_router_registers_routes_on_fastapi_router() -> None:
    endpoint, _, _, _, _, _ = _build_endpoint()
    endpoint_contract = cast(EndpointContract, endpoint)
    route = Route("/items", ["GET"], ["items"], endpoint_contract)
    router = APIRouter()
    custom_router = Router(router)

    result = custom_router([cast(RouteContract, route)])

    assert result is router
    assert any(getattr(r, "path", None) == "/items" for r in router.routes)


@pytest.mark.asyncio
async def test_endpoint_callable_runs_pipeline_and_response_adapter() -> None:
    endpoint, request_adapter, response_describer, pipeline, parameter, interceptor = _build_endpoint()
    handler = endpoint()

    signature = inspect.signature(handler)
    assert "item_id" in signature.parameters
    assert signature.return_annotation is ResponseModel

    callable_handler = cast(Awaitable[Response], handler(item_id=7))
    response = await callable_handler

    assert isinstance(response, Response)
    assert response.status_code == 201
    assert pipeline.captured_messages is not None
    assert isinstance(pipeline.captured_messages[0], DummyTask)
    assert interceptor.received_messages
