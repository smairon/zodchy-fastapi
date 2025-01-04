import abc
import collections.abc

import fastapi
import jwt

default_access_denied_adapter = lambda r: fastapi.responses.ORJSONResponse(
    status_code=401,
    content={"data": {"code": 401, "message": "Access denied", "details": None}},
)


class AuthMiddleware(abc.ABC):
    def __init__(
        self,
        access_denied_response_adapter: collections.abc.Callable[
            [
                fastapi.Request,
            ],
            fastapi.Response,
        ] = default_access_denied_adapter,
        public_paths: list[str] = None,
    ):
        self._public_paths = public_paths
        self._access_denied_response_adapter = access_denied_response_adapter

    @abc.abstractmethod
    async def __call__(self, request: fastapi.Request, call_next):
        raise NotImplemented

    def _is_public_path(self, request) -> bool:
        for public_path in self._public_paths or ():
            if request.url.path.startswith(public_path):
                return True


class JwtAuthMiddleware(AuthMiddleware):
    def __init__(
        self,
        auth_context_registrator: collections.abc.Callable[
            [fastapi.Request, dict], bool
        ],
        jwt_algorithm: str = "HS256",
        access_denied_response_adapter: collections.abc.Callable[
            [fastapi.Request], fastapi.Response
        ] = default_access_denied_adapter,
        public_paths: list[str] = None,
    ):
        super().__init__(access_denied_response_adapter, public_paths)
        self._auth_context_registrator = auth_context_registrator
        self._jwt_algorithm = jwt_algorithm

    async def __call__(self, request: fastapi.Request, call_next) -> fastapi.Response:
        if self._is_public_path(request):
            return await call_next(request)

        access_token = request.headers.get("Authorization", "").replace("Bearer", "").strip()
        if not access_token:
            return self._access_denied_response_adapter(request)

        try:
            payload = jwt.decode(
                access_token,
                request.app.jwt_secret,
                algorithms=[self._jwt_algorithm],
            )
        except jwt.exceptions.PyJWTError:
            return self._access_denied_response_adapter(request)

        if not payload:
            return self._access_denied_response_adapter(request)

        if self._auth_context_registrator(request, payload):
            return await call_next(request)

        return self._access_denied_response_adapter(request)


class GatewayAuthMiddleware(AuthMiddleware):
    def __init__(
        self,
        auth_context_registrator: collections.abc.Callable[
            [fastapi.Request], bool
        ],
        access_denied_response_adapter: collections.abc.Callable[
            [fastapi.Request], fastapi.Response
        ] = default_access_denied_adapter,
        public_paths: list[str] = None,
    ):
        self._auth_context_registrator = auth_context_registrator
        super().__init__(access_denied_response_adapter, public_paths)

    async def __call__(self, request: fastapi.Request, call_next) -> fastapi.Response:
        if self._is_public_path(request):
            return await call_next(request)

        if self._auth_context_registrator(request):
            return await call_next(request)

        return self._access_denied_response_adapter(request)
