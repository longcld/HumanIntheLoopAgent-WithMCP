from typing import TypedDict
from langchain_core.messages import BaseMessage


class BaseState(TypedDict):
    """Base state for all agents."""

    messages: list[BaseMessage]

    session_id: str
    previous_node: str = None
    next_node: str = None
