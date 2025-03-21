import os
import datetime
from fastapi import APIRouter, UploadFile, File, Form, Query

from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from backend.db.db import get_session
from backend.AudioProcessing.schema import RecordingResponse, GetRecording
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.auth.jwt_handler import verify_token
from backend.config import TenantSettings
from backend.schemas.RoleSchema import RoleEnum
from backend.Store.StoreModel import Store
from backend.Area.AreaModel import Area
from backend.User.UserModel import User
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

    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID missing from token")
    CallRecoding = upload_recording_service(
        Recording, staff_id, start_time, end_time, CallDuration, db, token
    )
    return RecordingResponse(
        id=CallRecoding.id,
        staff_id=CallRecoding.staff_id,
        start_time=CallRecoding.start_time,
        end_time=CallRecoding.end_time,
        call_duration=CallRecoding.call_duration,
        audio_length=CallRecoding.audio_length,
        file_url=CallRecoding.file_url,
    )
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
            user_role = RoleEnum(role_str)
        except ValueError:
            raise HTTPException(
                status_code=403, detail="Invalid user role provided in token."
            )

        query = (
            db.query(
                VoiceRecording,
                Store.store_name,
                Area.area_name
            )
            .join(User, VoiceRecording.user_id == User.id)
            .join(Store, User.store_id == Store.store_id)
            .join(Area, Store.area_id == Area.area_id)
        )
        if user_role == RoleEnum.L0:
            query = query.filter(VoiceRecording.user_id == user_id)
        elif user_role == RoleEnum.L3 or user_role == RoleEnum.L4:
            pass  # Fetch all records
        else:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access this resource.",
            )

        recordings = query.all()

        if not recordings:
            raise HTTPException(status_code=404, detail="No recordings found")
            
        return [
            GetRecording(
                staff_id=rec.VoiceRecording.user_id,
                start_time=rec.VoiceRecording.start_time,
                end_time=rec.VoiceRecording.end_time,
                call_duration=rec.VoiceRecording.call_duration,
                audio_length=rec.VoiceRecording.audio_length,
                listening_time=rec.VoiceRecording.listening_time or 0.0, 
                file_url=rec.VoiceRecording.file_url,
                store_name=rec.store_name,
                area_name=rec.area_name,
                created_at=rec.VoiceRecording.created_at,
                modified_at=rec.VoiceRecording.modified_at,
            )
            for rec in recordings
        ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recordings: {e}")

# @router.get("/get-last-recording", response_model=GetRecording)
# def get_last_recording(
#     user_id: str = Query(None, description="User ID to fetch the last recording for"),
#     db: Session = Depends(get_session),
#     token: dict = Depends(verify_token),
# ):
#     try:
#         token_user_id = token.get("user_id")
#         role_str = token.get("role")

#         if not token_user_id:
#             raise HTTPException(status_code=401, detail="Unauthorized")

#         try:
#             user_role = RoleEnum(role_str)
#         except ValueError:
#             raise HTTPException(
#                 status_code=403, detail="Invalid user role provided in token."
#             )

#         if user_id is None:
#             user_id = token_user_id

#         if user_role == RoleEnum.L0 and user_id != token_user_id:
#             raise HTTPException(
#                 status_code=403,
#                 detail="You don't have permission to access other users' recordings.",
#             )

#         query = db.query(VoiceRecording).filter(VoiceRecording.user_id == user_id)

#         last_recording = query.order_by(VoiceRecording.created_at.desc()).first()

#         if not last_recording:
#             raise HTTPException(status_code=404, detail="No recordings found")

#         return GetRecording(
#             staff_id=last_recording.staff_id,
#             start_time=last_recording.start_time,
#             end_time=last_recording.end_time,
#             call_duration=last_recording.call_duration,
#             audio_length=last_recording.audio_length,
#             file_url=last_recording.file_url,
#             created_at=last_recording.created_at,
#             modified_at=last_recording.modified_at,
#         )

#     except Exception as e:
#         raise HTTPException(
#             status_code=500, detail=f"Error fetching last recording: {e}"
#         )


@router.get("/get-daily-recording-hours", response_model=dict)
def get_daily_recording_hours(
    time_period: str = Query(
        "week", description="Filter by 'week', 'month', or 'year'"
    ),
    user_id: str = Query(None, description="User ID to fetch recording hours for"),
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        token_user_id = token.get("user_id")
        role_str = token.get("role")

        if not token_user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

        try:
            user_role = RoleEnum(role_str)
        except ValueError:
            raise HTTPException(
                status_code=403, detail="Invalid user role provided in token."
            )

        if user_id is None:
            user_id = token_user_id

        if user_role == RoleEnum.L0 and user_id != token_user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access other users' recordings.",
            )

        today = datetime.utcnow()
        if time_period == "week":
            start_date = today - timedelta(
                days=today.weekday()
            )
        elif time_period == "month":
            start_date = today.replace(day=1)
        elif time_period == "year":
            start_date = today.replace(month=1, day=1)
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid time period. Use 'week', 'month', or 'year'.",
            )

        daily_hours = (
            db.query(
                cast(VoiceRecording.start_time, Date).label("recording_date"),
                func.sum(VoiceRecording.call_duration).label("total_duration"),
            )
            .filter(VoiceRecording.user_id == user_id)
            .filter(VoiceRecording.start_time >= start_date)
            .group_by(cast(VoiceRecording.start_time, Date))
            .all()
        )

        if not daily_hours:
            raise HTTPException(status_code=404, detail="No recordings found")

        return {
            "user_id": user_id,
            "time_period": time_period,
            "daily_recording_hours": {
                str(record.recording_date): round(record.total_duration / 3600, 2)
                for record in daily_hours
            },
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching daily recording hours: {e}"
        )


@router.get("/recordings-insights", response_model=dict)
def get_recordings_insights(
    user_id: str = Query(None, description="User ID to fetch insights for"),
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        token_user_id = token.get("user_id")
        role_str = token.get("role")

        if not token_user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")
        try:
            user_role = RoleEnum(role_str)
        except ValueError:
            raise HTTPException(
                status_code=403, detail="Invalid user role provided in token."
            )

        if user_id is None:
            user_id = token_user_id

        if user_role == RoleEnum.L0 and user_id != token_user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access other users' recordings.",
            )

        total_seconds = (
            db.query(func.sum(VoiceRecording.call_duration))
            .filter(VoiceRecording.user_id == user_id)
            .scalar()
        ) or 0
        total_hours = total_seconds / 3600

        total_recordings = (
            db.query(func.count(VoiceRecording.id))
            .filter(VoiceRecording.user_id == user_id)
            .scalar()
        ) or 0

        avg_length = (
            db.query(func.avg(VoiceRecording.call_duration))
            .filter(VoiceRecording.user_id == user_id)
            .scalar()
        )
        avg_minutes = round(avg_length / 60, 2) if avg_length else 0

        hourly_counts = (
            db.query(
                func.extract("hour", VoiceRecording.start_time).label("hour_of_day"),
                func.count().label("call_count"),
            )
            .filter(VoiceRecording.user_id == user_id)
            .group_by(func.extract("hour", VoiceRecording.start_time))
            .order_by(func.count().desc())
            .all()
        )

        peak_hours = {
            int(record.hour_of_day): record.call_count for record in hourly_counts
        }

        total_listening_seconds = (
            db.query(func.sum(VoiceRecording.listening_time))
            .filter(VoiceRecording.user_id == user_id)
            .scalar()
        ) or 0
        total_listening_hours = total_listening_seconds / 3600

        last_listening = (
            db.query(VoiceRecording.last_listening_time)
            .filter(VoiceRecording.user_id == user_id)
            .order_by(VoiceRecording.last_listening_time.desc())
            .first()
        )
        last_listening_time = last_listening[0] if last_listening else None

        return {
            "user_id": user_id,
            "total_recording_hours": round(total_hours, 2),
            "total_recordings": total_recordings,
            "average_recording_length": avg_minutes,
            "peak_hours": peak_hours,
            "total_listening_hours": round(total_listening_hours, 2),
            "last_listening_time": last_listening_time,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching recordings insights: {e}"
        )


@router.put("/update-listening-time", response_model=dict)
def update_listening_time(
    recording_id: str = Form(..., description="ID of the recording"),
    listening_time: float = Form(
        ..., description="Time in seconds user listened to the recording"
    ),
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        token_user_id = token.get("user_id")
        if not token_user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

        recording = (
            db.query(VoiceRecording).filter(VoiceRecording.id == recording_id).first()
        )
        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")

        recording.listening_time = listening_time
        recording.last_listening_time = datetime.utcnow()
        db.commit()
        db.refresh(recording)

        return {
            "message": "Listening time updated successfully",
            "recording_id": recording_id,
            "updated_listening_time": recording.listening_time,
            "last_listening_time": recording.last_listening_time,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error updating listening time: {e}"
        )

@router.delete("/delete-recording/{recording_id}", response_model=dict)
def delete_recording(
    recording_id: str,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        token_user_id = token.get("user_id")
        role_str = token.get("role")
        if not token_user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

        try:
            user_role = RoleEnum(role_str)
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid user role.")

        if user_role != RoleEnum.L3:
            raise HTTPException(status_code=403, detail="Only admins can delete recordings.")

        recording = db.query(VoiceRecording).filter(VoiceRecording.id == recording_id).first()

        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")

        db.delete(recording)
        db.commit()
        return {"message": "Recording deleted successfully", "recording_id": recording_id}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting recording: {e}")
