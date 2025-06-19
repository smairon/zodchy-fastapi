import typing
import fastapi
import zodchy


class TaskExecutorContract(typing.Protocol):
    async def run(
        self,
        task: zodchy.codex.cqea.Task,
        execution_context: dict[str, typing.Any] | None = None,
    ) -> list[zodchy.codex.cqea.Message]: ...


class Application(fastapi.FastAPI):
    task_executor: TaskExecutorContract
