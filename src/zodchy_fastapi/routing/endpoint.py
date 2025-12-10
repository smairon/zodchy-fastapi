import collections.abc
import inspect
from typing import Any

import fastapi
from zodchy.codex.cqea import Message

from ..definition.contracts import (
    AsyncMessageStreamContract,
    PypelineCodeType,
    PypelineRegistryContract,
    RequestDescriberContract,
    RequestParameterContract,
    ResponseDescriberContract,
    ResponseModel,
)


class Batch:
    def __init__(
        self,
        *messages: Message,
    ):
        self._messages = list(messages) if messages else []

    def append(self, message: Message) -> None:
        self._messages.append(message)

    @property
    def message_type(self) -> type[Message] | None:
        return type(self._messages[0]) if self._messages else None

    def __iter__(self) -> collections.abc.Generator[Message, None, None]:
        yield from self._messages


class Endpoint:
    def __init__(
        self,
        request: RequestDescriberContract,
        response: ResponseDescriberContract,
        pipeline_code: PypelineCodeType,
    ):
        self.request = request
        self.response = response
        self._pipline_code = pipeline_code

    def __call__(self, pipeline_registry: PypelineRegistryContract) -> collections.abc.Callable[..., fastapi.Response]:
        async def func(**kwargs: Any) -> fastapi.Response | None:
            if self._pipline_code not in pipeline_registry:
                raise RuntimeError(f"Pipeline '{self._pipline_code}' is not registered")

            params: dict[str, RequestParameterContract] = {}
            for parameter in self.request.get_schema():
                if parameter.get_name() in kwargs:
                    parameter.set_value(kwargs[parameter.get_name()])
                    params[parameter.get_name()] = parameter
            tasks = self.request.get_adapter()(**params)

            stream = pipeline_registry[self._pipline_code](*tasks)

            async for batch in self._group_stream(stream):
                for interceptor in self.response.get_interceptors():
                    if batch.message_type is not None and issubclass(
                        batch.message_type, interceptor.get_desired_type()
                    ):
                        return interceptor(*batch)

            return None

        sig = inspect.signature(func)
        _params = [v for v in sig.parameters.values() if v.name != "kwargs"]
        _exists = {v.name for v in _params}
        for parameter in self.request.get_schema():
            if parameter.get_name() in _exists:
                continue
            _exists.add(parameter.get_name())
            _params.append(
                inspect.Parameter(
                    parameter.get_name(),
                    inspect.Parameter.POSITIONAL_OR_KEYWORD,
                    annotation=parameter.get_type(),
                    default=inspect.Parameter.empty,
                )
            )
        func.__signature__ = sig.replace(parameters=_params, return_annotation=ResponseModel)  # type: ignore
        return func  # type: ignore

    async def _group_stream(self, stream: AsyncMessageStreamContract) -> collections.abc.AsyncGenerator[Batch, None]:
        batch = None
        async for message in stream:
            if batch is None:
                batch = Batch(message)
                continue
            if batch.message_type is not None and isinstance(message, batch.message_type):
                batch.append(message)
            else:
                yield batch
                batch = Batch(message)
        if batch is not None:
            yield batch
