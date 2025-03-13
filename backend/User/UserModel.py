import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, func, Enum
from sqlalchemy.orm import declarative_base, relationship
from backend.schemas.StatusSchema import StatusEnum
from backend.schemas.RoleSchema import RoleEnum
Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())  # Replace this with cuid.cuid() if using CUIDs

class User(Base):
    __tablename__ = "user"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    password = Column(String(256), nullable=False)
    email = Column(String(255), nullable =False)
    user_role = Column(Enum(RoleEnum), nullable=False, default=RoleEnum.L0)
    business_key = Column(String(255), nullable=False)
    store_id = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp(),nullable=False)
    modified_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp(),nullable=False)
    user_status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.ACTIVE)
