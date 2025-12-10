import abc
from collections.abc import Callable
from typing import Any, cast

from zodchy.codex.cqea import Message, View


class Serializer(abc.ABC):
    def __init__(
        self,
        message_serializer: Callable[[Message], Any] | None = None,
    ):
        self._message_serializer = message_serializer

    @abc.abstractmethod
    def __call__(self, *messages: Message) -> Any:
        raise NotImplementedError()


class ResponseMapping(Serializer):
    def __call__(self, *messages: Message) -> Any:
        if len(messages) == 1:
            data = self._message_serializer(messages[0]) if self._message_serializer else messages[0]
        else:
            data = [self._message_serializer(message) if self._message_serializer else message for message in messages]
        return {
            "data": data,
        }


class ViewMapping(Serializer):
    def __call__(self, *messages: Message) -> Any:
        if len(messages) == 0:
            return {"data": []}
        view = cast(View, messages[0])
        data = self._message_serializer(view.data()) if self._message_serializer else view.data()
        if meta := view.meta():
            return {
                "data": data,
                "meta": meta,
            }
        else:
            return {
                "data": data,
            }
