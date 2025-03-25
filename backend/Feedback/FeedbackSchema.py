from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Dict, Union, Any


class FeedbackCreate(BaseModel):
    staff_id: str
    audio_id: str
    feedback: Union[Dict[str, Any], str] 
    Billed: str
    number: str


class FeedbackResponse(BaseModel):
    id: str
    user_id: str
    staff_id: str
    feedback: str
    created_at: datetime
    modified_at: datetime
    staff_name: str
    staff_email: str
    number: Optional[str]
    Billed: Optional[str]


class Feedback(BaseModel):
    id: str
    user_id: str
    staff_id: str
    feedback: str
    created_at: datetime
    modified_at: datetime
    staff_name: str
    staff_email: str
    number: Optional[str]
    Billed: Optional[str]
    audio_url: Optional[str]