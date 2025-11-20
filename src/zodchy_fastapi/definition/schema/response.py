from typing import Generic, TypeVar

import pydantic

# ----------------------Generic----------------------

T = TypeVar("T")


class ResponseData(pydantic.BaseModel):
    pass


class ResponseModel(pydantic.BaseModel, Generic[T]):
    data: T


# ----------------------Data----------------------


class ErrorResponseData(ResponseData):
    code: int
    message: str
    details: dict | None


class PaginatedListMetaData(ResponseData):
    quantity: int


# ----------------------Models----------------------
class ErrorResponseModel(ResponseModel[ErrorResponseData]):
    pass


class ItemResponseModel(ResponseModel[ResponseData]):
    pass


class ListResponseModel(ResponseModel[list[ResponseData]]):
    pass


class PaginatedListResponseModel(ListResponseModel):
    meta: PaginatedListMetaData
