import os
import datetime
from fastapi import APIRouter, UploadFile, File, Form

# from sqlalchemy import DateTime
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from backend.db.db import get_session
from backend.AudioProcessing.schema import RecordingResponse
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.auth.jwt_handler import verify_token
from backend.config import TenantSettings
from backend.AudioProcessing.service import upload_recording


router = APIRouter()
settings = TenantSettings()


@router.post("/upload-recording", response_model=RecordingResponse)
def upload_recording(
    Recording: UploadFile = File(...),
    start_time: datetime = Form(None),
    end_time: datetime = Form(None),
    staff_id: str = Form(None),
    CallDuration: str = Form(None),
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    CallRecoding = upload_recording(
        Recording, staff_id, start_time, end_time, CallDuration, db, token
    )

    return {
        "Status": 1,
        "Msg": "Created Successfully",
        "CallRecordingKey": CallRecoding,
    }
