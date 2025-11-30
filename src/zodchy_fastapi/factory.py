from typing import Any

from zodchy_fastapi.definition.schema.request import RequestModel
from zodchy_fastapi.definition.schema.response import ResponseModel


def make_response_class(data_class: type) -> type[ResponseModel[Any]]:
    """
    Create a ResponseModel class dynamically based on the provided data_class.
    @param data_class: The data class to be used as the 'data' field in the ResponseModel.
    @return: A new ResponseModel class with the specified data_class.
    """
    class_name = f"{data_class.__name__}Response"

    # Create annotations for the new class
    annotations = {"data": data_class}

    # Create the class using type()
    new_class = type(
        class_name,
        (ResponseModel,),
        {"__annotations__": annotations, "data": None},
    )
    return new_class


def make_request_class(data_class: type) -> type[RequestModel]:
    """
    Create a RequestModel class dynamically based on the provided data_class.
    @param data_class: The data class to be used as the 'data' field in the RequestModel.
    @return: A new RequestModel class with the specified data_class.
    """
    class_name = f"{data_class.__name__}Request"

    # Create annotations for the new class
    annotations = {"data": data_class}

    # Create the class using type()
    new_class = type(
        class_name,
        (RequestModel,),
        {"__annotations__": annotations, "data": None},
    )
    return new_class
