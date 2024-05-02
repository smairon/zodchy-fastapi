import collections.abc
import typing

import zodchy

from . import schema


class ResponseData(typing.TypedDict):
    status_code: int
    content: typing.Any


AdapterContract = collections.abc.Callable[
    [zodchy.codex.cqea.EventStream | ResponseData, type[schema.Response] | None],
    schema.Response
]


class Adapter:
    def __init__(
        self,
        picker: collections.abc.Callable[[zodchy.codex.cqea.EventStream], zodchy.codex.cqea.Event],
        default_response_class: type[schema.Response]
    ):
        self._picker = picker
        self._default_response_class = default_response_class

    def __call__(
        self,
        data: zodchy.codex.cqea.EventStream | ResponseData,
        response_class: type[schema.Response] | None = None
    ) -> schema.Response:
        response_class = response_class or self._default_response_class
        if isinstance(data, collections.abc.Mapping):
            return response_class(
                **data
            )
        if data := self._picker(data):
            if data.get_content() is None:
                return schema.EmptyResponse(status_code=data.get_status_code())
            else:
                return response_class(
                    status_code=data.get_status_code(),
                    content=data.get_content()
                )
        else:
            return schema.EmptyResponse(status_code=200)
