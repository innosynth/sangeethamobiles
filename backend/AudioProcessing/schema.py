from pydantic import BaseModel
from datetime import datetime

# class UploadRecodingBody(BaseModel):
#     file: bytes
#     staff_id:str


class RecordingResponse(BaseModel):
    user_id:str