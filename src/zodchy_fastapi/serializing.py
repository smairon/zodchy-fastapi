import abc
from collections.abc import Callable
from typing import Any

from zodchy.codex.cqea import Message


class Serializer(abc.ABC):
    def __init__(
        self,
        message_serializer: Callable[[Message], Any],
    ):
        self._message_serializer = message_serializer

    @abc.abstractmethod
    def __call__(self, *messages: Message) -> Any:
        raise NotImplementedError()


class ResponseMapping(Serializer):
    def __call__(self, *messages: Message) -> Any:
        if len(messages) == 1:
            data = self._message_serializer(messages[0])
        else:
            data = [self._message_serializer(message) for message in messages]
        return {
            "data": data,
        }
