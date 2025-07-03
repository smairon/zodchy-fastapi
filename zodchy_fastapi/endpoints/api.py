import inspect

from fastapi import Request

from ..schema.response import ResponseModel
from ..contracts import TaskExecutorContract
from ..internal.contracts import RequestAdapter, ResponseAdapter


def zodchy_endpoint(
    request_adapter: RequestAdapter,
    response_adapter: ResponseAdapter,
    task_executor: TaskExecutorContract,
):
    async def func(request: Request, **kwargs):
        params = kwargs | ({"request": request} if request_adapter.need_request else {})
        task = request_adapter.executable(**params)
        stream = await task_executor.run(task)
        return response_adapter.executable(
            **(
                {"stream": stream}
                | ({"request": request} if response_adapter.need_request else {})
            )
        )

    sig = inspect.signature(func)
    _params = [v for v in sig.parameters.values() if v.name != "kwargs"]
    _exists = set([v.name for v in _params])
    for name, annotation in request_adapter.params.items():
        if name in _exists:
            continue
        _exists.add(name)
        _params.append(
            inspect.Parameter(
                name,
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                annotation=annotation,
                default=inspect.Parameter.empty,
            )
        )
    func.__signature__ = sig.replace(
        parameters=_params, return_annotation=ResponseModel
    )
    return func
