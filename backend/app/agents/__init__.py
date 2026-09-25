"""The five cooperating AGENT X agents."""

from app.agents.base import AgentContext, BaseAgent
from app.agents.classification import ClassificationAgent
from app.agents.drafting import DraftingAgent
from app.agents.filing import FilingAgent
from app.agents.intake import IntakeAgent
from app.agents.watchdog import WatchdogAgent

ALL_AGENTS: tuple[type[BaseAgent], ...] = (  # type: ignore[type-arg]
    IntakeAgent,
    ClassificationAgent,
    DraftingAgent,
    FilingAgent,
    WatchdogAgent,
)

__all__ = [
    "ALL_AGENTS",
    "AgentContext",
    "BaseAgent",
    "ClassificationAgent",
    "DraftingAgent",
    "FilingAgent",
    "IntakeAgent",
    "WatchdogAgent",
]
