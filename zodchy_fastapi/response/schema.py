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


class ResponseModel(pydantic.BaseModel):
    data: ResponseData


class ErrorResponseModel(ResponseModel):
    data: ErrorResponseData


class ItemResponseModel(ResponseModel):
    pass


class ListResponseModel(ResponseModel):
    pass


class PaginatedListResponseModel(ResponseModel):
    data: list[ResponseData]
    quantity: int
