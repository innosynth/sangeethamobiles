from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List


# from enum import Enum
from datetime import datetime
from backend.schemas.StatusSchema import StatusEnum
from backend.schemas.RoleSchema import RoleEnum


class UserCreate(BaseModel):
    name: str
    password: str
    email_id: EmailStr
    user_code: Optional[str] = None
    user_ph_no: Optional[str] = None
    reports_to: Optional[str] = None
    business_id: str
    role: RoleEnum


class CreateUserResponse(BaseModel):
    user_id: str
    name: str
    email_id: EmailStr
    user_code: Optional[str] = None
    user_ph_no: Optional[str] = None
    reports_to: Optional[str] = None
    business_id: str
    role: RoleEnum
    status: StatusEnum
    created_at: datetime
    modified_at: datetime

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    user_id: str
    name: str
    email_id: EmailStr
    user_code: str | None
    user_ph_no: str | None
    reports_to: str | None
    business_id: str
    role: RoleEnum
    store_name: str
    area_name: str
    created_at: datetime
    modified_at: datetime
    status: StatusEnum
    recording_hours: float
    listening_hours: float
    recording_count: int

    class Config:
        from_attributes = True


class StaffResponse(BaseModel):
    staff_id: str
    name: str
    email_id: str
    affilated_user_id: str
    store_id: str


class StaffCreate(BaseModel):
    name: str
    email_id: str


class UserUpdateSchema(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    email_id: Optional[EmailStr] = (
        None  # Changed from 'email' to 'email_id' (matches User model)
    )
    user_code: Optional[str] = Field(
        None, min_length=1, max_length=50
    )  # Added user_code field
    user_ph_no: Optional[str] = Field(
        None, min_length=10, max_length=15
    )  # Phone number field
    reports_to: Optional[str] = Field(
        None, min_length=1, max_length=36
    )  # Manager's user ID
    role: Optional[RoleEnum] = None  # Changed from 'user_role' to 'role'
    status: Optional[StatusEnum] = None  # Changed from 'user_status' to 'status'

    class Config:
        from_attributes = True


class UserUpdateResponse(BaseModel):
    message: str
    user_id: str
    updated_fields: List[str]


class StaffResponses(BaseModel):
    id: str
    name: str
    email_id: EmailStr
    affiliated_user_id: str
    created_at: datetime
    modified_at: datetime
    staff_status: StatusEnum

    class Config:
        from_attributes = True
