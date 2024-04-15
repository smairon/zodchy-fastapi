import dataclasses
import typing
import pydantic
import fastapi

import zodchy

Response = fastapi.responses.Response


class ResponseModel(pydantic.BaseModel):
    pass


class DataModel(pydantic.BaseModel):
    pass


class QueryResultResponseModel(ResponseModel):
    data: typing.Any


class ErrorDataModel(ResponseModel):
    code: int
    message: str
    details: dict | None


class ValidationErrorDataModel(ErrorDataModel):
    code: int = 422
    message: str = "Validation Error"
    details: list[ErrorDataModel]


class ErrorResponseModel(ResponseModel):
    data: ErrorDataModel


class DefaultErrorResponseModel(ResponseModel):
    data: ErrorDataModel


class ValidationFailResponseModel(ErrorResponseModel):
    data: ValidationErrorDataModel


class PaginationModel(ResponseModel):
    quantity: int


class PaginatedResponseModel(QueryResultResponseModel):
    pagination: PaginationModel


@dataclasses.dataclass
class ResponseEvent(zodchy.codex.Event):
    payload: typing.Any


class ResponseErrorPayloadData(typing.TypedDict):
    code: int
    message: str
    details: dict | None


class ResponseErrorPayload(typing.TypedDict):
    data: ResponseErrorPayloadData


@dataclasses.dataclass
class ResponseError(zodchy.codex.Error):
    payload: typing.Any
    status_code: int = 500
