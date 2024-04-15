import collections.abc

import fastapi


def generic_exception_handler(
    request: fastapi.Request,
    exc: Exception
):
    return fastapi.responses.ORJSONResponse(
        status_code=500,
        content={
            "data": {
                "code": 500,
                "message": "Unknown exception",
                "details": str(exc)
            }
        }
    )


def validation_exception_handler(
    request: fastapi.Request,
    exc: fastapi.exceptions.ValidationException
):
    details = {}
    for e in exc.errors():
        details = _merge(details, _nestify(e['loc'], e['msg']))
    return fastapi.responses.ORJSONResponse(
        status_code=422,
        content={
            "data": {
                "code": 422,
                "message": "Validation error",
                "details": details
            }
        }
    )


def _nestify(data: collections.abc.Sequence[str] | str, value: str):
    if len(data) > 1:
        value = _nestify(data[1:], value)
    return {
        data[0]: value
    }


def _merge(d1: dict, d2: dict):
    for k, v in d2.items():
        if k in d1 and isinstance(v, dict):
            d1[k] |= v
        else:
            d1[k] = v
    return d1
