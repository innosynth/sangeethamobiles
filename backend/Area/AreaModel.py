import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, func, Enum
from sqlalchemy.orm import declarative_base, relationship
from backend.schemas.StatusSchema import StatusEnum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())  # Replace this with cuid.cuid() if using CUIDs


class Area(Base):
    __tablename__ = "area"

    area_id = Column(String(36), primary_key=True, default=generate_uuid)
    area_name = Column(String(255), nullable=False)
    area_manager_name = Column(String(255), nullable=False)
    sales_id = Column(String(36), nullable=False)  # Foreign key linking to Sales table
    created_at = Column(DateTime, default=func.current_timestamp())
    modified_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    # Relationship to Sales table
    # sales = relationship("Sales", back_populates="areas")
