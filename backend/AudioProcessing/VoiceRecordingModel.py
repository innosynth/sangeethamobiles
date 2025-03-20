import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, func
from sqlalchemy.orm import declarative_base, relationship
from backend.schemas.StatusSchema import StatusEnum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())


class VoiceRecording(Base):
    __tablename__ = "voice_recording"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), nullable=False)
    staff_id = Column(String(36), nullable=False)
    audio_length = Column(Float, nullable=False)
    file_url = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    call_duration = Column(Float, nullable=False)
    listening_time = Column(Float, nullable=True)
    last_listening_time = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
    created_at = Column(DateTime, default=func.current_timestamp())
    modified_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )
