import uuid
import fastapi
from zodchy.codex.cqea import Command, Message, Event
from fastapi.responses import JSONResponse
from zodchy_fastapi import definition, routing, request, response, serializer


class CreateUserCommand(Command):
    first_name: str
    last_name: str


class UserCreatedEvent(Event):
    user_id: str
    first_name: str
    last_name: str


class CreateUser(definition.schema.request.RequestData):
    first_name: str
    last_name: str


class UserCreated(definition.schema.response.ResponseData):
    user_id: str
    first_name: str
    last_name: str


def make_response_class(data_class: type) -> type[definition.schema.response.ResponseModel]:
    class_name = f"{data_class.__name__}Response"

    # Создаем аннотации для нового класса
    annotations = {"data": data_class}

    # Создаем класс с помощью type()
    new_class = type(
        class_name, (definition.schema.response.ResponseModel,), {"__annotations__": annotations, "data": None}
    )
    return new_class


def make_request_class(data_class: type) -> type[definition.schema.request.RequestModel]:
    class_name = f"{data_class.__name__}Request"

    # Создаем аннотации для нового класса
    annotations = {"data": data_class}

    # Создаем класс с помощью type()
    new_class = type(
        class_name, (definition.schema.request.RequestModel,), {"__annotations__": annotations, "data": None}
    )
    return new_class


async def pipeline(*messages: Message):
    async for message in messages:
        yield UserCreatedEvent(
            user_id=str(uuid.uuid4()),
            first_name=message.first_name,
            last_name=message.last_name,
        )


def bootstrap_pipeline():
    return pipeline


def bootstrap_routes():
    return [
        routing.Route(
            path="/users/{user_id}",
            methods=["POST"],
            tags=["test"],
            endpoint=routing.Endpoint(
                request_adapter=request.DeclarativeAdapter(
                    parameters=[
                        request.ModelParameter(
                            type=make_request_class(CreateUser),
                        ),
                        request.RouteParameter(
                            name="user_id",
                            type=uuid.UUID,
                        ),
                    ],
                    message_type=CreateUserCommand,
                ),
                response_adapter=response.DeclarativeAdapter(
                    response.Interceptor(
                        catch=UserCreatedEvent,
                        response=(200, make_response_class(UserCreated)),
                        format=(JSONResponse, serializer.ResponseMapping(lambda event: event.model_dump())),
                    ),
                ),
                pipeline=bootstrap_pipeline(),
            ),
        ),
    ]


def server_example():
    router = routing.Router(fastapi.APIRouter())(bootstrap_routes())
    app = fastapi.FastAPI()
    app.include_router(router)
    return app


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(server_example(), host="0.0.0.0", port=8005)
