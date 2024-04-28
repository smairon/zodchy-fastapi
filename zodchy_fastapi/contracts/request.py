import pydantic
import fastapi.params


class Request(fastapi.Request):
    pass


class RequestModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    pass
