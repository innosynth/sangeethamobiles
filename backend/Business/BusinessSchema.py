from datetime import datetime
from pydantic import BaseModel
from backend.schemas.StatusSchema import StatusEnum


class BusinessCreate(BaseModel):
    business_id: str
    business_name: str
    business_status: StatusEnum
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = (
            True  # This allows SQLAlchemy models to be converted to Pydantic models
        )
