from pydantic import BaseModel
from typing import Optional
from enum import Enum


class Message(BaseModel):
    message_id: str
    user_id: str
    session_id: str
    role: str
    content: Optional[str] = ""
