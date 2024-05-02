import collections.abc

import fastapi

from .. import contracts


def generic_exception_handler(
    request: contracts.Request,
    exc: Exception
):
    return request.app.response_adapter(
        dict(
            status_code=500,
            content={
                "data": {
                    "code": 500,
                    "message": "Unknown exception",
                    "details": str(exc)
                }
            }
        )
    )


def validation_exception_handler(
    request: contracts.Request,
    exc: fastapi.exceptions.ValidationException
):
    details = {}
    for e in exc.errors():
        details = _merge(details, _nestify(e['loc'], e['msg']))
    return request.app.response_adapter(
        dict(
            status_code=422,
            content={
                "data": {
                    "code": 422,
                    "message": "Validation error",
                    "details": details
                }
            }
        )
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
