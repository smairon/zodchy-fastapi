import abc
import typing

import pydantic
import fastapi

Response = fastapi.responses.Response


class EmptyResponse(Response):
    pass


class ResponseData(pydantic.BaseModel):
    pass


class ErrorResponseData(ResponseData):
    code: int
    message: str
    details: dict | None


class ResponseModel(pydantic.BaseModel, abc.ABC):
    data: typing.Any


class ErrorResponseModel(ResponseModel):
    data: ErrorResponseData


class ItemResponseModel(ResponseModel):
    data: ResponseData


class ListResponseModel(ResponseModel):
    data: list[ResponseData]


class PaginatedListResponseModel(ListResponseModel):
    quantity: int
