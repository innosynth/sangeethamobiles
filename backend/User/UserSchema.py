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
