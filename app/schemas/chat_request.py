from pydantic import BaseModel, Field
from typing import Optional, List
from .message import Message


class ChatRequest(BaseModel):
    user_id: str = Field(
        ...,
        title='User ID',
        description='Unique identifier for the user making the request',
        example='123456'
    )
    session_id: str = Field(
        ...,
        title='Session ID',
        description='Unique identifier for the session associated with the request',
        example='session_abc'
    )
    message: str = Field(
        ...,
        title="User's message content",
        description='The question or prompt the user is asking',
        example='hi xin chao'
    )
    messages: Optional[List[dict]] = Field(
        default=[],
        title='Conversation History',
        description='Full conversation history for context',
        example=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
    )
    previous_node: Optional[str] = Field(
        default=None,
        title='Previous Node',
        description='The previous node in the agent workflow for state tracking',
        example='orchestrate'
    )
    current_plan: Optional[str] = Field(
        default="",
        title='Current Plan',
        description='The current plan being executed by the agent',
        example='Analyze user request and provide response'
    )
    params: dict = Field(
        default={},
        title='Parameters',
        description='Additional parameters for the chat request',
        example={}
    )
