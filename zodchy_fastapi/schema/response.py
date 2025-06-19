import abc

import pydantic
import fastapi

## ----------------------Response Data Models----------------------


class ResponseData(pydantic.BaseModel):
    pass


class ErrorResponseData(ResponseData):
    code: int
    message: str
    details: dict | None


class PaginatedListMetaData(ResponseData):
    quantity: int


class ResponseModel(pydantic.BaseModel, abc.ABC):
    data: ResponseData


## ----------------------Error Response Models----------------------


class ErrorResponseModel(ResponseModel):
    data: ErrorResponseData


class NotFoundResponseModel(ErrorResponseModel):
    data: ErrorResponseData


class ConflictResponseModel(ErrorResponseModel):
    data: ErrorResponseData


class ValidationErrorResponseModel(ErrorResponseModel):
    data: ErrorResponseData


class NotAuthorizedResponseModel(ErrorResponseModel):
    data: ErrorResponseData


class ForbiddenResponseModel(ErrorResponseModel):
    data: ErrorResponseData


class InternalServerErrorResponseModel(ErrorResponseModel):
    data: ErrorResponseData


## ----------------------Success Response Models----------------------


class ItemResponseModel(ResponseModel):
    data: ResponseData


class CreatedResponseModel(ResponseModel):
    data: ResponseData


class ListResponseModel(ResponseModel):
    data: list[ResponseData]


class PaginatedListResponseModel(ListResponseModel):
    meta: PaginatedListMetaData


class EmptyResponseModel(fastapi.responses.Response):
    pass
