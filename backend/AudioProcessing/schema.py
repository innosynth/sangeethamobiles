from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# class UploadRecodingBody(BaseModel):
#     file: bytes
#     staff_id:str


class RecordingResponse(BaseModel):
    id: str
    staff_id: str
    start_time: datetime
    end_time: datetime
    call_duration: float
    audio_length: float
    file_url: str


class GetRecording(BaseModel):
    user_id: str
    start_time: datetime
    end_time: datetime
    call_duration: float
    audio_length: float
    listening_time: float
    file_url: str
    store_name: Optional[str] = None  # Allowing None if missing
    area_name: Optional[str] = None   # Allowing None if missing
    created_at: datetime
    modified_at: datetime
