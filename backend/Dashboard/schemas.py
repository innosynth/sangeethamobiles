from pydantic import BaseModel
from datetime import datetime


class LastLogin(BaseModel):
    user_id: str
    last_login: datetime


class AvailableStaff(BaseModel):
    user_id: str
    staff_id: str
