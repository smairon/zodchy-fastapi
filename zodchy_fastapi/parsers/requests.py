import collections
from zodchy.codex.query import NotationParser, ClauseBit
from ..schema.request import RequestModel, FilterParam

class QueryRequestParser:
    def __init__(
        self,
        notation_parser: NotationParser
    ):
        self._notation_parser = notation_parser

    def __call__(
        self,
        request_model: RequestModel,
        fields_map: collections.abc.Mapping[str, str] | None = None
    ) -> collections.abc.Mapping[str, ClauseBit]:
        fields_map = fields_map or {}
        return {
            fields_map.get(t[0], t[0]): t[1] for t in self._notation_parser(
                request_model.model_dump(exclude_none=True, exclude_unset=True),
                self._types_map(request_model)
            )
        }

    @staticmethod
    def _types_map(payload_model: RequestModel):
        result = {}
        for field_name, field_info in payload_model.model_fields.items():
            for e in field_info.metadata:
                if isinstance(e, FilterParam):
                    result[field_name] = e.type
                    break
        return result