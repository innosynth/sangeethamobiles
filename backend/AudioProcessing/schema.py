from pydantic import BaseModel
from datetime import datetime

# class UploadRecodingBody(BaseModel):
#     file: bytes
#     staff_id:str


class RecordingResponse(BaseModel):
    user_id: str

    user_id: str


class GetRecording(BaseModel):
    staff_id: str
    start_time: datetime
    end_time: datetime
    call_duration: float
    audio_length: float
    file_url: str
    created_at: datetime
    modified_at: datetime
