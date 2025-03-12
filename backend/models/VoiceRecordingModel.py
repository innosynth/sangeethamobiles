import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, func
from sqlalchemy.orm import declarative_base, relationship
from backend.schemas.StatusSchema import StatusEnum
Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())  # Replace this with cuid.cuid() if using CUIDs

class VoiceRecording(Base):
    __tablename__ = "voice_recording"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False)
    audio_length = Column(Float, nullable=False)
    transcription_id = Column(String(36), nullable=True)
    file_url = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    modified_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # user = relationship("User", back_populates="recordings")
    # transcription = relationship("Transcription", back_populates="recording")
