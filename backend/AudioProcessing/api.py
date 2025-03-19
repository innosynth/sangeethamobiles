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
    print(CallRecoding.__dict__)
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


@router.get("/get-last-recording", response_model=GetRecording)
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

        query = db.query(VoiceRecording).filter(VoiceRecording.user_id == user_id)

        last_recording = query.order_by(VoiceRecording.created_at.desc()).first()

        if not last_recording:
            raise HTTPException(status_code=404, detail="No recordings found")

        return GetRecording(
            staff_id=last_recording.staff_id,
            start_time=last_recording.start_time,
            end_time=last_recording.end_time,
            call_duration=last_recording.call_duration,
            audio_length=last_recording.audio_length,
            file_url=last_recording.file_url,
            created_at=last_recording.created_at,
            modified_at=last_recording.modified_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching last recording: {e}"
        )


@router.get("/get-total-recording-hours", response_model=dict)
def get_total_recording_hours(
    user_id: str = Query(
        None, description="User ID to fetch total recording hours for"
    ),
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
        )

        if total_seconds is None:
            total_seconds = 0

        total_hours = total_seconds / 3600

        return {"user_id": user_id, "total_recording_hours": round(total_hours, 2)}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error calculating recording hours: {e}"
        )


@router.get("/get-total-recordings", response_model=dict)
def get_total_recordings(
    user_id: str = Query(None, description="User ID to fetch total recordings for"),
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

        # Query to count total recordings for the user
        total_recordings = (
            db.query(func.count(VoiceRecording.id))
            .filter(VoiceRecording.user_id == user_id)
            .scalar()
        )

        return {"user_id": user_id, "total_recordings": total_recordings}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching total recordings: {e}"
        )


@router.get("/get-avg-recording-length", response_model=dict)
def get_avg_recording_length(
    user_id: str = Query(
        None, description="User ID to fetch average recording length for"
    ),
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

        # Query to calculate average recording length
        avg_length = (
            db.query(func.avg(VoiceRecording.call_duration))
            .filter(VoiceRecording.user_id == user_id)
            .scalar()
        )
        avg_minutes = avg_length / 60
        if avg_minutes is None:
            raise HTTPException(status_code=404, detail="No recordings found")

        return {"user_id": user_id, "average_recording_length": avg_minutes}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching average recording length: {e}"
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

        # Get date filters
        today = datetime.utcnow()
        if time_period == "week":
            start_date = today - timedelta(
                days=today.weekday()
            )  # Start of the week (Monday)
        elif time_period == "month":
            start_date = today.replace(day=1)  # First day of the month
        elif time_period == "year":
            start_date = today.replace(month=1, day=1)  # First day of the year
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid time period. Use 'week', 'month', or 'year'.",
            )

        # Query to get total hours recorded per day
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


@router.get("/get-peak-recording-hours", response_model=dict)
def get_peak_recording_hours(
    user_id: str = Query(None, description="User ID to fetch peak recording hours for"),
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

        hourly_avg = (
            db.query(
                func.extract("hour", VoiceRecording.start_time).label("hour_of_day"),
                func.avg(VoiceRecording.call_duration).label("avg_duration"),
            )
            .filter(VoiceRecording.user_id == user_id)
            .group_by(func.extract("hour", VoiceRecording.start_time))
            .order_by(
                func.avg(VoiceRecording.call_duration).desc()
            )  # Order by max avg duration
            .all()
        )

        if not hourly_avg:
            raise HTTPException(status_code=404, detail="No recordings found")

        peak_hours = {
            int(record.hour_of_day): round(record.avg_duration / 60, 2)
            for record in hourly_avg
        }

        return {"user_id": user_id, "peak_hours": peak_hours}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching peak recording hours: {e}"
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

        hourly_avg = (
            db.query(
                func.extract("hour", VoiceRecording.start_time).label("hour_of_day"),
                func.avg(VoiceRecording.call_duration).label("avg_duration"),
            )
            .filter(VoiceRecording.user_id == user_id)
            .group_by(func.extract("hour", VoiceRecording.start_time))
            .order_by(func.avg(VoiceRecording.call_duration).desc())
            .all()
        )

        peak_hours = {
            int(record.hour_of_day): round(record.avg_duration / 60, 2)
            for record in hourly_avg
        }

        return {
            "total_recording_hours": round(total_hours, 2),
            "total_recordings": total_recordings,
            "average_recording_length": avg_minutes,
            "peak_hours": peak_hours,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching recordings insights: {e}"
        )
