import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, func, Enum
from sqlalchemy.orm import declarative_base, relationship
from backend.schemas.StatusSchema import StatusEnum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())  # Replace this with cuid.cuid() if using CUIDs


class Store(Base):
    __tablename__ = "store"

    store_id = Column(String(36), primary_key=True, default=generate_uuid)
    store_name = Column(String(255), nullable=False)
    store_code = Column(String(100), nullable=False)
    store_address = Column(Text, nullable=False)
    district = Column(String(100), nullable=False)
    state = Column(String(100), nullable=False)
    store_status = Column(Enum(StatusEnum), nullable=False, default=StatusEnum.ACTIVE)
    business_id = Column(String(36), nullable=False)
    area_id = Column(String(36), nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    modified_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    # business = relationship("Business", back_populates="stores")
    # area = relationship("Area", back_populates="stores")
