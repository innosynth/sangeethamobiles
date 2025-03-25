from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List


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


class CreateUserResponse(BaseModel):
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


class UserResponse(BaseModel):
    id: str
    name: str
    email: EmailStr
    user_role: RoleEnum
    business_key: str
    store_id: str
    store_name: str
    created_at: datetime
    modified_at: datetime
    user_status: StatusEnum
    recording_hours: float
    listening_hours: float
    area_name: str
    recording_count: int
    store_name: str

    class Config:
        from_attributes = True


class StaffResponse(BaseModel):
    name: str
    email_id: str
    affilated_user_id: str


class StaffCreate(BaseModel):
    name: str
    email_id: str

class UserUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = None
    user_role: Optional[RoleEnum] = None
    business_key: Optional[str] = Field(None, min_length=1, max_length=50)
    store_id: Optional[str] = Field(None, min_length=1, max_length=36)
    user_status:Optional[StatusEnum] = None


class UserUpdateResponse(BaseModel):
    message: str
    user_id: str
    updated_fields: List[str]