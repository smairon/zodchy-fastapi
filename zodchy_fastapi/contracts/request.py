import collections.abc
import dataclasses
import functools
import inspect

import pydantic
import fastapi.params
import zodchy


class Request(fastapi.Request):
    pass


class InputParam:
    pass


class OrderParam(InputParam):
    def __init__(self, *fields):
        super().__init__()
        self.fields = fields


class LimitParam(InputParam):
    pass


class OffsetParam(InputParam):
    pass


class FieldSetParam(InputParam):
    pass


class FilterParam(InputParam):
    def __init__(self, param_type: type):
        self._param_type = param_type

    @property
    def type(self):
        return self._param_type


class RequestModel(pydantic.BaseModel, extra=pydantic.Extra.forbid):
    @functools.cached_property
    def _parser(self):
        return zodchy.notations.math.Parser(
            types_map=self._compile_types_map(),
            parsing_schema=zodchy.notations.math.ParsingSchema(
                **self._compile_schema_params()
            )
        )

    def _compile_types_map(self) -> collections.abc.Mapping:
        result = {}
        for k, v in self.model_fields.items():
            if _type := self._search_filter_field_type(v):
                result[k] = _type
        return result

    def _compile_schema_params(self):
        result = dict(
            order_by=None,
            limit=None,
            offset=None,
            fieldset=None
        )
        _schema = {
            OrderParam: 'order_by',
            LimitParam: 'limit',
            OffsetParam: 'offset',
            FieldSetParam: 'fieldset'
        }
        for k, v in self.model_fields.items():
            if f := _schema.get(type(self._search_schema_field_type(v))):
                result[f] = k
        return result

    def __call__(self, message: zodchy.codex.Command | zodchy.codex.Query):
        _type = 'class' if inspect.isclass(message) else 'object'
        _names = {f.name for f in dataclasses.fields(message)}
        message_params = {}
        for input_param in self:
            if input_param.name in _names:
                if input_param.name in message_params:
                    value = message_params[input_param.name]
                else:
                    value = getattr(message, input_param.name) if _type == 'object' else None
                if value is None:
                    value = input_param.value
                elif isinstance(value, zodchy.codex.query.ClauseBit):
                    value += input_param.value
                message_params[input_param.name] = value

        if _type == 'class':
            message = message(**message_params)
        else:
            for k, v in message_params.items():
                setattr(message, k, v)

        return message

    def __iter__(self) -> collections.abc.Generator[zodchy.codex.query.Param]:
        yield from self._parser(
            {k: getattr(self, k) for k in self.model_fields_set}
        )

    @staticmethod
    def _search_filter_field_type(field_info: fastapi.params.FieldInfo) -> type | None:
        for item in field_info.metadata:
            if isinstance(item, FilterParam):
                return item.type

    @staticmethod
    def _search_schema_field_type(field_info: fastapi.params.FieldInfo) -> InputParam | None:
        for item in field_info.metadata:
            if isinstance(item, InputParam) and not isinstance(item, FilterParam):
                return item
