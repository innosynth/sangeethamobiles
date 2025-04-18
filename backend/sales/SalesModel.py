import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, func, Enum
from sqlalchemy.orm import declarative_base, relationship
from backend.schemas.StatusSchema import StatusEnum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())  # Replace this with cuid.cuid() if using CUIDs


class L2(Base):
    __tablename__ = "L2"
    L2_id = Column(String(36), primary_key=True, default=generate_uuid)
    L2_name = Column(String(255), nullable=True)  # region name
    user_id = Column(String(36), nullable=False)
    status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.ACTIVE)
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=True)
    modified_at = Column(
        DateTime,
        default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=True,
    )
