import uuid
from sqlalchemy import Column, String, Text, DateTime, func, JSON
from sqlalchemy.orm import declarative_base, relationship
from backend.schemas.StatusSchema import StatusEnum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())  # Replace this with cuid.cuid() if using CUIDs


class Transcription(Base):
    __tablename__ = "transcription"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    audio_id = Column(String(36), nullable=False)
    transcription_text = Column(Text, nullable=False)
    AI_analytics_id = Column(String(36), nullable=True)
    ML_analytics_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    modified_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

class TranscribeAI(Base):
    __tablename__ = "transcribe_ai"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    audio_id = Column(String(36), nullable=False)
    
    gender = Column(String(255), default="unknown")
    language = Column(String(255), default="unknown")
    emotional_state = Column(JSON, default=[])
    product_mentions = Column(JSON, default=[])
    complaints = Column(JSON, default=[])
    positive_keywords = Column(JSON, default=[])
    negative_keywords = Column(JSON, default=[])
    contact_reason = Column(JSON, default=[])