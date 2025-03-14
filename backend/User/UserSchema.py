from pydantic import BaseModel, EmailStr
# from enum import Enum
from datetime import datetime
from backend.schemas.StatusSchema import StatusEnum
from backend.schemas.RoleSchema import RoleEnum


class UserCreate(BaseModel):
    name: str
    password: str
    email: EmailStr
    user_role: RoleEnum 
    business_key: str
    store_id: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    user_role: RoleEnum
    business_key: str
    store_id: str
    created_at: datetime
    modified_at: datetime
    user_status: StatusEnum

    class Config:
        from_attributes = True  
