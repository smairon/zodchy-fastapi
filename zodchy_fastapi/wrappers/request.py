import functools
from ..schema.response import ResponseModel


def request_handler(skip=False):
    def decorator(func):
        func.__dict__['__request_handler__'] = True

        if skip:
            func.__dict__['__skip_handler__'] = skip

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapper

    return decorator
