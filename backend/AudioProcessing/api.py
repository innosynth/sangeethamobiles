import os
import datetime
from fastapi import APIRouter, UploadFile, File, Form, Query
from typing import List, Optional
from sqlalchemy import func, cast, Date
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from backend.User.service import extract_users
from backend.db.db import get_session
from backend.AudioProcessing.schema import RecordingResponse, GetRecording
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.auth.jwt_handler import verify_token
from backend.config import TenantSettings
from backend.schemas.RoleSchema import RoleEnum
from backend.Store.StoreModel import L0
from backend.Area.AreaModel import L1
from backend.User.UserModel import User
from backend.AudioProcessing.service import extract_recordings, upload_recording as upload_recording_service
from backend.auth.role_checker import check_role

router = APIRouter()
settings = TenantSettings()


@router.post("/upload-recording", response_model=RecordingResponse)
def upload_recording(
    Recording: UploadFile = File(...),
    start_time: datetime = Form(None),
    end_time: datetime = Form(None),
    staff_id: str = Form(None),
    CallDuration: str = Form(None),
    store_id: str = Form(None),
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):

    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=400, detail="User ID missing from token")
    CallRecoding = upload_recording_service(
        Recording, staff_id, start_time, end_time, CallDuration, store_id, db, token
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


@router.get("/get-recordings", response_model=List[GetRecording])
async def get_recordings(
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    store_id: Optional[str] = None,
):
    user_id = token.get("user_id")
    user_role = token.get("role")

    start_date_obj, end_date_obj = parse_dates(start_date, end_date)
    
    recordings = extract_recordings(db, user_id, user_role, start_date_obj, end_date_obj, store_id)

    return [
        GetRecording(
            recording_id=rec.id,
            user_id=rec.user_id,
            store_id=rec.store_id,
            start_time=rec.start_time,
            end_time=rec.end_time,
            call_duration=rec.call_duration,
            audio_length=rec.audio_length,
            listening_time=rec.listening_time or 0.0,
            file_url=rec.file_url,
            store_name=rec.store_name,
            store_code=rec.store_code,
            store_address=rec.store_address,
            asm_name=rec.asm_name,
            created_at=rec.created_at,
            modified_at=rec.modified_at,
        )
        for rec in recordings
    ]

def parse_dates(start_date: Optional[str], end_date: Optional[str]):
    try:
        if not start_date or not end_date:
            end_date_obj = datetime.utcnow()
            start_date_obj = end_date_obj - timedelta(days=30)
        else:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)

            if start_date_obj.date() == end_date_obj.date():
                end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)

        if start_date_obj > end_date_obj:
            raise HTTPException(status_code=400, detail="Start date must be before end date")
        
        return start_date_obj, end_date_obj
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

@router.get("/get-last-recording", response_model=GetRecording)
@check_role([RoleEnum.L1, RoleEnum.L2, RoleEnum.L3, RoleEnum.L4])
def get_last_recording(
    user_id: str = Query(None, description="User ID to fetch the last recording for"),
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

        query = (
            db.query(
                VoiceRecording,
                L0.L0_name.label("store_name"),
                User.name.label("asm_name"),  # Fetch ASM name from User table
            )
            .join(User, VoiceRecording.user_id == User.user_id)
            .outerjoin(L0, User.user_id == L0.user_id)
            .outerjoin(L1, L0.user_id == L1.user_id)
            .filter(VoiceRecording.user_id == user_id)
            .order_by(VoiceRecording.created_at.desc())
        )

        last_recording = query.first()

        if not last_recording:
            raise HTTPException(status_code=404, detail="No recordings found")

        return GetRecording(
            recording_id=last_recording.VoiceRecording.id,
            user_id=last_recording.VoiceRecording.user_id,
            start_time=last_recording.VoiceRecording.start_time,
            end_time=last_recording.VoiceRecording.end_time,
            call_duration=last_recording.VoiceRecording.call_duration,
            audio_length=last_recording.VoiceRecording.audio_length,
            listening_time=last_recording.VoiceRecording.listening_time or 0.0,
            file_url=last_recording.VoiceRecording.file_url,
            store_name=last_recording.store_name or "Unknown",
            # area_name=last_recording.area_name or "Unknown",
            asm_name=last_recording.asm_name
            or "Unknown",  # Include asm_name in response
            created_at=last_recording.VoiceRecording.created_at,
            modified_at=last_recording.VoiceRecording.modified_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching last recording: {e}"
        )


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

        today = datetime.utcnow().date()  # Get just the date part
        if time_period == "week":
            # Calculate Monday of the current week
            start_date = today - timedelta(days=today.weekday())
            # If today is Monday, include only today
            if today.weekday() == 0:
                end_date = today
            else:
                end_date = today
        elif time_period == "month":
            start_date = today.replace(day=1)
            end_date = today
        elif time_period == "year":
            start_date = today.replace(month=1, day=1)
            end_date = today
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
            .filter(VoiceRecording.start_time <= end_date + timedelta(days=1))  # Include the entire end date
            .group_by(cast(VoiceRecording.start_time, Date))
            .order_by("recording_date")  # Ensure chronological order
            .all()
        )

        if not daily_hours:
            raise HTTPException(status_code=404, detail="No recordings found")

        # Convert seconds to hours and format the response
        response = {
            "user_id": user_id,
            "time_period": time_period,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily_recording_hours": {
                record.recording_date.isoformat(): round(record.total_duration / 3600, 2)
                for record in daily_hours
            },
        }

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching daily recording hours: {str(e)}"
        )

@router.get("/recordings-insights", response_model=dict)
def get_recordings_insights(
    user_id: Optional[str] = Query(None, description="User ID to fetch insights for"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
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
            raise HTTPException(status_code=403, detail="Invalid user role provided in token.")

        start_date_obj, end_date_obj = parse_dates(start_date, end_date)

        if user_id:
            user_reports = extract_users(token_user_id, user_role, db)
            allowed_user_ids = {user.user_id for user in user_reports}

            if user_id not in allowed_user_ids:
                raise HTTPException(
                    status_code=403,
                    detail="You don't have permission to access this user's insights.",
                )

            user_ids = [user_id]
        else:
            user_reports = extract_users(token_user_id, user_role, db)
            user_ids = [user.user_id for user in user_reports]

        filters = [
            VoiceRecording.user_id.in_(user_ids),
            VoiceRecording.created_at >= start_date_obj,
            VoiceRecording.created_at <= end_date_obj,
        ]

        # Fetch Insights
        total_seconds = db.query(func.sum(VoiceRecording.call_duration)).filter(*filters).scalar() or 0
        total_hours = total_seconds / 3600

        total_recordings = db.query(func.count(VoiceRecording.id)).filter(*filters).scalar() or 0

        avg_length = db.query(func.avg(VoiceRecording.call_duration)).filter(*filters).scalar()
        avg_minutes = round(avg_length / 60, 2) if avg_length else 0

        hourly_counts = (
            db.query(
                func.extract("hour", VoiceRecording.start_time).label("hour_of_day"),
                func.count().label("call_count"),
            )
            .filter(*filters)
            .group_by(func.extract("hour", VoiceRecording.start_time))
            .order_by(func.count().desc())
            .all()
        )

        peak_hours = {int(record.hour_of_day): record.call_count for record in hourly_counts}

        # Total listening time
        total_listening_seconds = db.query(func.sum(VoiceRecording.listening_time)).filter(*filters).scalar() or 0
        total_listening_hours = total_listening_seconds / 3600

        last_listening = (
            db.query(VoiceRecording.last_listening_time)
            .filter(*filters)
            .order_by(VoiceRecording.last_listening_time.desc())
            .first()
        )
        last_listening_time = last_listening[0] if last_listening else None

        return {
            "user_id": user_id if user_id else token_user_id,
            "total_recording_hours": round(total_hours, 2),
            "total_recordings": total_recordings,
            "average_recording_length": avg_minutes,
            "peak_hours": peak_hours,
            "total_listening_hours": round(total_listening_hours, 2),
            "last_listening_time": last_listening_time,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recordings insights: {e}")


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

        if user_role != RoleEnum.L4:
            raise HTTPException(
                status_code=403, detail="Only admins can delete recordings."
            )

        recording = (
            db.query(VoiceRecording).filter(VoiceRecording.id == recording_id).first()
        )

        if not recording:
            raise HTTPException(status_code=404, detail="Recording not found")

        db.delete(recording)
        db.commit()
        return {
            "message": "Recording deleted successfully",
            "recording_id": recording_id,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error deleting recording: {e}")
