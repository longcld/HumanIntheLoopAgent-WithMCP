from .base import BaseState


class State(BaseState):
    """State specific to the orchestrator agent."""

    current_plan: str = ""
    metadata: dict = {}
