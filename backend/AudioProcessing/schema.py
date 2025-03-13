from pydantic import BaseModel
from datetime import datetime


class VoiceRecordingCreate(BaseModel):
    user_id: str
    audio_length: float
    file_url: str
    start_time: datetime
    end_time: datetime
    call_duration: float
