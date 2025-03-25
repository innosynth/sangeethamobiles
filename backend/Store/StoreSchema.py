from pydantic import BaseModel, Field
from datetime import datetime
from backend.schemas.StatusSchema import StatusEnum
from typing import Optional, List



class StoreCreate(BaseModel):
    store_name: str
    store_code: str
    store_address: str
    district: str
    state: str
    store_status: StatusEnum
    business_id: str
    area_id: str
    lat: str
    long: str
    pin_code: str
    store_ph_no: str


class StoreResponse(StoreCreate):
    store_id: str
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class StoreSummary(BaseModel):
    store_id: str
    store_name: str
    store_code:str
    district: str
    state: str

    class Config:
        from_attributes = True

class StoreUpdateSchema(BaseModel):
    store_name: Optional[str] = Field(None, min_length=1, max_length=100)
    store_code: Optional[str] = Field(None, min_length=1, max_length=50)
    store_address: Optional[str] = Field(None, min_length=1, max_length=255)
    district: Optional[str] = Field(None, min_length=1, max_length=100)
    state: Optional[str] = Field(None, min_length=1, max_length=100)
    store_status: Optional[bool] = None
    business_id: Optional[str] = Field(None, min_length=1, max_length=36)
    area_id: Optional[str] = Field(None, min_length=1, max_length=36)

class StoreUpdateResponse(BaseModel):
    message: str
    store_id: str
    updated_fields: List[str]