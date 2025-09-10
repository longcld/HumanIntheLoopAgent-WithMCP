from .base import BaseState


class PlanState(BaseState):
    """State specific to the orchestrator agent."""

    current_plan: str = ""
    plan_history: list[str] = []
    is_approved: bool = False
