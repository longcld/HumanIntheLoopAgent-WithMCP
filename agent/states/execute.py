from typing import Any
from .base import BaseState
from langchain_core.messages import BaseMessage, ToolMessage


class ExecutionState(BaseState):
    """State specific to the execution agent."""

    plan: str = ""
    steps: list[str] = []
    current_step: int = 0
    approval_status: str = "not_requested"  # not_requested, pending, approved, rejected

    tool_message: BaseMessage
    is_tool_calling: bool = False
    tool_outputs: list[ToolMessage] = []
