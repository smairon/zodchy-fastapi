from zodchy import codex

from .. import contracts


class QueryAdapter:
    def __init__(
        self,
        notation_parser: codex.query.NotationParser
    ):
        self._notation_parser = notation_parser

    def __call__(
        self,
        request_model: contracts.RequestModel,
        target_model: type[codex.cqea.Query]
    ) -> codex.cqea.Query:
        return target_model(
            **{
                t[0]: t[1] for t in self._notation_parser(
                    request_model.model_dump(exclude_none=True, exclude_unset=True),
                    self._types_map(request_model)
                )
            }
        )

    @staticmethod
    def _types_map(payload_model: contracts.RequestModel):
        result = {}
        for field_name, field_info in payload_model.model_fields.items():
            for e in field_info.metadata:
                if isinstance(contracts.request.FilterParam, e):
                    result[field_name] = e.type
                    break
        return result
