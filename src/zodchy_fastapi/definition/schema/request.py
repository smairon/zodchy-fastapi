from typing import Any

import pydantic


class QueryParam:
    pass


class FilterParam(QueryParam):
    def __init__(self, param_type: type):
        self._param_type = param_type

    @property
    def type(self) -> type:
        return self._param_type


class OrderParam(QueryParam):
    def __init__(self, *fields: Any):
        super().__init__()
        self.fields = fields


class LimitParam(QueryParam):
    pass


class OffsetParam(QueryParam):
    pass


class FieldSetParam(QueryParam):
    pass


class RequestData(pydantic.BaseModel, extra="forbid"):
    pass


class RequestModel(pydantic.BaseModel, extra="forbid"):
    data: RequestData | list[RequestData]
