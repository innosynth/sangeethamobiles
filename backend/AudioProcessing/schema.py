from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from backend.schemas.TranscriptionSchema import TransctriptionStatus

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
    recording_id: str
    user_id: str
    store_id: Optional[str] = None
    start_time: datetime
    end_time: datetime
    call_duration: float
    audio_length: float
    listening_time: float
    file_url: str
    store_name: Optional[str] = None  # Allowing None if missing
    # area_name: Optional[str] = None   # Allowing None if missing
    store_code: Optional[str] = None
    store_address: Optional[str] = None
    asm_name: str
    created_at: datetime
    modified_at: datetime
    transcription_status: Optional[TransctriptionStatus] = None
    transcription_text: Optional[str] = None
    transcription_id: Optional[str] = None

class GetLastRecording(BaseModel):
    recording_id: str
    user_id: str
    start_time: datetime
    end_time: datetime
    call_duration: float
    audio_length: float
    listening_time: float
    file_url: str
    store_name: Optional[str] = None  # Allowing None if missing
    # area_name: Optional[str] = None   # Allowing None if missing
    asm_name: str
    created_at: datetime
    modified_at: datetime