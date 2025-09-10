from .base import BaseState


class ExecutionState(BaseState):
    """State specific to the execution agent."""

    plan: str = ""
    steps: list[str] = []
    current_step: int = 0
