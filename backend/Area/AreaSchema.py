from pydantic import BaseModel

class AreaCreate(BaseModel):
    area_name: str
    sales_id: str  # UUID as a string

class AreaResponse(AreaCreate):
    area_id: str

class AreaSummary(BaseModel):
    area_id: str
    area_name: str
    sales_id: str
