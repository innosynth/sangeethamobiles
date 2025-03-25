import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, func
from sqlalchemy.orm import declarative_base, relationship
from backend.schemas.StatusSchema import StatusEnum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())  # Replace this with cuid.cuid() if using CUIDs


class FeedbackModel(Base):
    __tablename__ = "feedback"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    audio_id = Column(String(36), nullable=False)
    user_id = Column(String(36), nullable=False)
    created_by = Column(String(36), nullable=False)
    number = Column(String(36), nullable=False)
    Billed = Column(String(36))
    feedback = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    modified_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
