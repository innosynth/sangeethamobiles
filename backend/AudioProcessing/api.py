import os
import datetime
from fastapi import APIRouter, UploadFile, File, Form

# from sqlalchemy import DateTime
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from backend.db.db import get_session
from backend.AudioProcessing.schema import RecordingResponse, GetRecording
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.auth.jwt_handler import verify_token
from backend.config import TenantSettings
from backend.schemas.RoleSchema import RoleEnum

from backend.AudioProcessing.service import upload_recording as upload_recording_service

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

    CallRecoding = upload_recording_service(
        Recording, staff_id, start_time, end_time, CallDuration, db, token
    )

    user_id = token.get("user_id")

    if not user_id:
        raise HTTPException(status_code=400, detail="User ID missing from token")

    return RecordingResponse(user_id=user_id)


@router.get("/get-recordings", response_model=list[GetRecording])
def get_recording(
    db: Session = Depends(get_session), token: dict = Depends(verify_token)
):

    try:
        user_id = token.get("user_id")
        role_str = token.get("role")
        if not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

        try:
            # role_int = int(role_str.lstrip("L"))
            user_role = RoleEnum(role_str)
        except ValueError:
            raise HTTPException(
                status_code=403, detail="Invalid user role provided in token."
            )
        if user_role == RoleEnum.L0:
            recordings = (
                db.query(VoiceRecording).filter(VoiceRecording.user_id == user_id).all()
            )
        elif user_role == RoleEnum.L3:
            recordings = db.query(VoiceRecording).filter().all()
        else:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this resource.",
            )

        if not recordings:
            raise HTTPException(status_code=404, detail="No recordings found")

        return [
            GetRecording(
                staff_id=rec.staff_id,
                start_time=rec.start_time,
                end_time=rec.end_time,
                call_duration=rec.call_duration,
                audio_length=rec.audio_length,
                file_url=rec.file_url,
                created_at=rec.created_at,
                modified_at=rec.modified_at,
            )
            for rec in recordings
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recordings: {e}")
