import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, func, Enum
from sqlalchemy.orm import declarative_base, relationship
from backend.schemas.StatusSchema import StatusEnum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())  # Replace this with cuid.cuid() if using CUIDs


class Sales(Base):
    __tablename__ = "sales"
    sales_id = Column(String(36), primary_key=True, default=generate_uuid)
    sales_head_name = Column(String(255), nullable=False)
    sales_area = Column(String(255), nullable=True)
    # sales_head_ph_no = Column(String(255), nullable= True)
    created_at = Column(DateTime, default=func.current_timestamp())
    modified_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )