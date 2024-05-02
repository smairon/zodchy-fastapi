import fastapi
from . import request, response


class Application(fastapi.FastAPI):
    request_adapter: request.AdapterContract
    response_adapter: response.AdapterContract


class Request(fastapi.Request):
    app: Application
