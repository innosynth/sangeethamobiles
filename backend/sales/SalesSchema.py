from typing import List
from pydantic import BaseModel


class RegionOut(BaseModel):
    region_id: str
    region_name: str
    region_email: str
    regional_manager_name: str

class RegionListResponse(BaseModel):
    regions: List[RegionOut]