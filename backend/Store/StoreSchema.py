from pydantic import BaseModel, Field
from datetime import datetime
from backend.schemas.StatusSchema import StatusEnum
from typing import Optional, List


class StoreCreate(BaseModel):
    store_name: str
    store_code: str
    store_address: str
    store_status: StatusEnum


class StoreResponse(StoreCreate):
    store_id: str
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class StoreSummary(BaseModel):
    L0_id: str
    L0_name: str
    L0_code: str
    L0_addr: str
    user_id: str
    status: StatusEnum
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class StoreUpdateSchema(BaseModel):
    L0_name: Optional[str] = Field(None, min_length=1, max_length=100)  # Store Name
    L0_code: Optional[str] = Field(None, min_length=1, max_length=50)  # Store Code
    L0_addr: Optional[str] = Field(None, min_length=1, max_length=255)  # Store Address
    status: Optional[StatusEnum] = None  # Store Status (ACTIVE/INACTIVE)


class StoreUpdateResponse(BaseModel):
    message: str
    store_id: str
    updated_fields: List[str]


class RegionRequest(BaseModel):
    Region_id: str


class RegionResponse(BaseModel):
    Stores: List[str]
    Users: List[str]
    total_recordings: int
    total_hours: float
    average_call_duration_minutes: float
    total_feedbacks: int
