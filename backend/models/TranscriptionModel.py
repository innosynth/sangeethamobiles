import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, func, Enum
from sqlalchemy.orm import declarative_base, relationship
from backend.schemas.StatusSchema import StatusEnum
Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())  # Replace this with cuid.cuid() if using CUIDs

class Transcription(Base):
    __tablename__ = "transcription"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    transcription_text = Column(Text, nullable=False)
    AI_analytics_id = Column(String(36), nullable=True)
    ML_analytics_id = Column(String(36), nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    modified_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # recording = relationship("VoiceRecording", back_populates="transcription")
    # ai_analytics = relationship("AIAnalytics", back_populates="transcription")
    # ml_analytics = relationship("MLAnalytics", back_populates="transcription")
