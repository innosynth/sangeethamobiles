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
    user_id = Column(String(36), primary_key=True, default=generate_uuid)  
    name = Column(String(255), nullable=False) # store manager  name
    email_id = Column(String(255), nullable=False) # email id
    user_code = Column(String(255), nullable=True) # user code
    password = Column(String(256), nullable=False) # password
    user_ph_no = Column(String(255), nullable=True) # user phone number
    reports_to = Column(String(36), nullable=True) # reports to / manager
    business_id = Column(String(36), nullable=False)
    role = Column(Enum(RoleEnum), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=True)
    modified_at = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=True,
    )
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.ACTIVE)
    
    

class Staff(Base):
    __tablename__ = "staff"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    email_id = Column(String(255), nullable=False)
    user_id = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    modified_at = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
    staff_status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.ACTIVE)
