from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict


class FeedbackCreate(BaseModel):
    staff_id: str
    feedback: Dict[str, str]
    Billed: str
    number: str


class FeedbackResponse(BaseModel):
    id: str
    user_id: str
    staff_id: str
    # feedback: str
    created_at: datetime
    modified_at: datetime
