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
from backend.Store.StoreModel import L0
from backend.Area.AreaModel import L1
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
    store_id:str = Form(None),
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

@router.get("/get-recordings", response_model=list[GetRecording])
def get_recording(
    db: Session = Depends(get_session), 
    token: dict = Depends(verify_token)
):
    try:
        # Get user details from token
        role_str = token.get("role")
        user_id = token.get("user_id")

        if not role_str or not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

        try:
            user_role = RoleEnum(role_str)
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid user role in token.")

        # Get all recordings
        recordings_query = db.query(VoiceRecording)
        
        # Role-based access control
        if user_role == RoleEnum.L0:
            recordings_query = recordings_query.filter(VoiceRecording.user_id == user_id)

        recordings = recordings_query.all()

        if not recordings:
            raise HTTPException(status_code=404, detail="No recordings found")

        # Get all unique store_ids from the recordings
        store_ids = list({rec.store_id for rec in recordings})

        # Get store information (L0) and user (ASM) details
        store_info = (
            db.query(
                L0.L0_id.label("store_id"),
                L0.L0_name.label("store_name"),
                L0.L0_code.label("store_code"),
                L0.L0_addr.label("store_address"),
                User.name.label("asm_name")  # ASM name from User table
            )
            .outerjoin(User, L0.user_id == User.user_id)  # Join with User to get ASM name
            .filter(L0.L0_id.in_(store_ids))
            .all()
        )

        # Create a mapping of store_id to store/ASM info
        store_data = {
            store.store_id: {
                "store_name": store.store_name,
                "store_code": store.store_code,
                "store_address": store.store_address,
                "asm_name": store.asm_name or "Unknown"
            }
            for store in store_info
        }

        # Prepare the response
        result = []
        for rec in recordings:
            store = store_data.get(rec.store_id, {
                "store_name": "Unknown",
                "store_code": "Unknown",
                "store_address": "Unknown",
                "asm_name": "Unknown"
            })
            
            result.append(GetRecording(
                recording_id=rec.id,
                user_id=rec.user_id,
                store_id=rec.store_id,
                start_time=rec.start_time,
                end_time=rec.end_time,
                call_duration=rec.call_duration,
                audio_length=rec.audio_length,
                listening_time=rec.listening_time or 0.0,
                file_url=rec.file_url,
                store_name=store["store_name"],
                store_code=store["store_code"],  # Include store code
                store_address=store["store_address"],  # Include store address
                asm_name=store["asm_name"],
                created_at=rec.created_at,
                modified_at=rec.modified_at,
            ))

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching recordings: {str(e)}")
    
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

        query = (
            db.query(
                VoiceRecording,
                L0.L0_name.label("store_name"),
                User.name.label("asm_name")  # Fetch ASM name from User table
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
            asm_name=last_recording.asm_name or "Unknown",  # Include asm_name in response
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
            raise HTTPException(status_code=403, detail="Invalid user role provided in token.")

        # If no user_id is provided, use the token’s user_id
        if user_id is None:
            user_id = token_user_id

        # L0 users can only see their own insights
        if user_role == RoleEnum.L0 and user_id != token_user_id:
            raise HTTPException(
                status_code=403,
                detail="You don't have permission to access other users' recordings.",
            )

        # 🚀 **Always filter by user_id (including L4 users now)**
        user_filter = VoiceRecording.user_id == user_id

        # Fetch Insights
        total_seconds = (
            db.query(func.sum(VoiceRecording.call_duration))
            .filter(user_filter)
            .scalar()
        ) or 0
        total_hours = total_seconds / 3600

        total_recordings = (
            db.query(func.count(VoiceRecording.id))
            .filter(user_filter)
            .scalar()
        ) or 0

        avg_length = (
            db.query(func.avg(VoiceRecording.call_duration))
            .filter(user_filter)
            .scalar()
        )
        avg_minutes = round(avg_length / 60, 2) if avg_length else 0

        hourly_counts = (
            db.query(
                func.extract("hour", VoiceRecording.start_time).label("hour_of_day"),
                func.count().label("call_count"),
            )
            .filter(user_filter)
            .group_by(func.extract("hour", VoiceRecording.start_time))
            .order_by(func.count().desc())
            .all()
        )

        peak_hours = {int(record.hour_of_day): record.call_count for record in hourly_counts}

        # Total listening time
        total_listening_seconds = (
            db.query(func.sum(VoiceRecording.listening_time))
            .filter(user_filter)
            .scalar()
        ) or 0
        total_listening_hours = total_listening_seconds / 3600

        last_listening = (
            db.query(VoiceRecording.last_listening_time)
            .filter(user_filter)
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
