import uuid
from sqlalchemy import Column, String, Text, DateTime, Float, ForeignKey, func, Enum
from sqlalchemy.orm import declarative_base, relationship
from backend.schemas.StatusSchema import StatusEnum

Base = declarative_base()


def generate_uuid():
    return str(uuid.uuid4())  # Replace this with cuid.cuid() if using CUIDs


class AIAnalytics(Base):
    __tablename__ = "ai_analytics"

    AI_analytics_id = Column(String(36), primary_key=True, default=generate_uuid)
    transcription_id = Column(String(36), nullable=False)
    top_emotion = Column(String(255), nullable=False)
    frequent_complaint = Column(Text, nullable=True)
    lead_interest = Column(Text, nullable=True)
    csat_score = Column(Float, nullable=True)
    usp = Column(Text, nullable=True)
    objection_handling = Column(Text, nullable=True)
    effectiveness = Column(Text, nullable=True)
    targeted_feedback = Column(Text, nullable=True)
    quality_assurance = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    modified_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    # transcription = relationship("Transcription", back_populates="ai_analytics")


class MLAnalytics(Base):
    __tablename__ = "ml_analytics"

    ML_analytics_id = Column(String(36), primary_key=True, default=generate_uuid)
    transcription_id = Column(String(36), nullable=False)
    sentiment = Column(String(255), nullable=False)
    sentiment_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=func.current_timestamp())
    modified_at = Column(
        DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp()
    )

    # transcription = relationship("Transcription", back_populates="ml_analytics")
