from .base import BaseState
from typing import TypedDict
from langchain_core.messages import BaseMessage


class State(TypedDict):
    """State specific to the orchestrator agent."""

    messages: list[BaseMessage]

    session_id: str

    previous_node: str = None
    next_node: str = None

    current_plan: str = ""
    plan_history: list[str] = []
