from datetime import datetime
from pydantic import BaseModel
from backend.schemas.StatusSchema import StatusEnum


class AreaCreate(BaseModel):
    area_name: str


class AreaResponse(BaseModel):
    area_id: str
    area_name: str
    user_id: str
    status: StatusEnum
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class AreaSummary(BaseModel):
    area_id: str
    area_name: str
    asm_name: str

    class Config:
        from_attributes = True
