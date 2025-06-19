from fastapi.responses import JSONResponse, ORJSONResponse


def exception_response_adapter(exc: Exception) -> JSONResponse:
    http_code = exc.http_code if hasattr(exc, "http_code") else 500
    semantic_code = exc.semantic_code if hasattr(exc, "semantic_code") else 500
    message = exc.message if hasattr(exc, "message") else str(exc)
    details = exc.details if hasattr(exc, "details") else None
    content = {
        "data": (
            {"code": semantic_code, "message": message}
            | ({"details": details} if details else {})
        )
    }
    try:
        return ORJSONResponse(status_code=http_code, content=content)
    except Exception as e:
        return JSONResponse(status_code=http_code, content=content)