import collections.abc
import typing

from .request import RequestModel

T = typing.TypeVar('T')

RequestModelAdapter = collections.abc.Callable[[RequestModel, type[T]], T]
