from pydantic import BaseModel
from datetime import datetime
from backend.schemas.StatusSchema import StatusEnum


class StoreCreate(BaseModel):
    store_name: str
    store_code: str
    store_address: str
    district: str
    state: str
    store_status: StatusEnum
    business_id: str
    area_id: str


class StoreResponse(StoreCreate):
    store_id: str
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True  
