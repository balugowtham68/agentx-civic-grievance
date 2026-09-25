"""Base abstraction shared by the five AGENT X agents.

Every agent:
- has a fixed identity (`name`, `description`, `phase`)
- declares a Pydantic input and output contract
- is executed through `execute()`, which validates input and output, times the
  run, logs it, and converts unexpected failures into AgentExecutionError

Subclasses implement only `_run()`. Agents never write to the database or call
external systems directly; they receive the services they need in __init__.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel, ValidationError

from app.core.clock import Clock, get_clock
from app.core.errors import AgentExecutionError, AppError
from app.core.logging import get_logger
from app.schemas.enums import AgentName

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)

logger = get_logger(__name__)


@dataclass
class AgentContext:
    """Per-run context passed to every agent."""

    complaint_id: str
    clock: Clock = field(default_factory=get_clock)
    correlation_id: str | None = None
    metadata: dict[str, object] = field(default_factory=dict)


class BaseAgent(ABC, Generic[InputT, OutputT]):
    name: ClassVar[AgentName]
    description: ClassVar[str]
    phase: ClassVar[int]  # implementation phase that delivers the behaviour
    input_model: ClassVar[type[BaseModel]]
    output_model: ClassVar[type[BaseModel]]

    async def execute(self, payload: InputT, context: AgentContext) -> OutputT:
        if not isinstance(payload, self.input_model):
            raise AgentExecutionError(
                f"{self.name.value} agent expected {self.input_model.__name__}, "
                f"got {type(payload).__name__}"
            )
        started = time.perf_counter()
        try:
            result = await self._run(payload, context)
            if not isinstance(result, self.output_model):
                raise AgentExecutionError(
                    f"{self.name.value} agent returned {type(result).__name__}, "
                    f"expected {self.output_model.__name__}"
                )
            return result
        except AppError:
            raise  # already meaningful (including NotImplementedYetError)
        except ValidationError as exc:
            raise AgentExecutionError(f"{self.name.value} agent produced invalid data: {exc}") from exc
        except Exception as exc:  # noqa: BLE001 - one failure boundary per agent
            logger.exception("agent failed", extra={"agent": self.name.value})
            raise AgentExecutionError(f"{self.name.value} agent failed") from exc
        finally:
            logger.info(
                "agent run",
                extra={
                    "agent": self.name.value,
                    "complaint_id": context.complaint_id,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 1),
                },
            )

    @abstractmethod
    async def _run(self, payload: InputT, context: AgentContext) -> OutputT:
        """Agent behaviour. Implemented in the agent's phase."""
