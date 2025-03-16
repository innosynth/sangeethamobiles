import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, func, Enum
from sqlalchemy.orm import declarative_base, relationship
from backend.schemas.StatusSchema import StatusEnum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())  # Replace this with cuid.cuid() if using CUIDs


class Business(Base):
    __tablename__ = "business"

    business_id = Column(String(36), primary_key=True, default=generate_uuid)
    business_name = Column(String(255), nullable=False)
    business_status = Column(
        Enum(StatusEnum), nullable=False, default=StatusEnum.PENDING
    )
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=True)
    modified_at = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=True,
    )
