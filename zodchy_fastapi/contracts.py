import typing
import zodchy

class ResponseError(Exception):
    def __init__(
        self,
        http_code: int,
        semantic_code: int,
        message: str,
        details: dict | None = None,
    ):
        self.http_code = http_code
        self.message = message
        self.details = details
        self.semantic_code = semantic_code
        super().__init__(self.message)

class TaskExecutorContract(typing.Protocol):
    async def run(
        self,
        task: zodchy.codex.cqea.Task,
        execution_context: dict[str, typing.Any] | None = None,
    ) -> list[zodchy.codex.cqea.Message]: ...