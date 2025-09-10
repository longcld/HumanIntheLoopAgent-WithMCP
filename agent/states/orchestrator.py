from .base import BaseState


class OrchestratorState(BaseState):
    """State specific to the orchestrator agent."""

    next_node: str
