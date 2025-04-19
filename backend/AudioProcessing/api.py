import io
import datetime
from fastapi import APIRouter, UploadFile,BackgroundTasks, File, Form, Query
from typing import List, Optional
from sqlalchemy import func, cast, Date
from datetime import date, datetime, timedelta
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from backend.State.stateModel import L3
from backend.User.service import extract_users
from backend.db.db import get_session
from backend.AudioProcessing.schema import RecordingResponse, GetRecording, GetLastRecording
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.auth.jwt_handler import verify_token
from backend.config import TenantSettings
from backend.sales.SalesModel import L2
from backend.Area.AreaModel import L1
from backend.schemas.RoleSchema import RoleEnum
from backend.Store.StoreModel import L0
from backend.AudioProcessing.schema import TransctriptionStatus
from backend.User.UserModel import User
from backend.AudioProcessing.service import (
    extract_recordings,
    upload_recording as upload_recording_service,
)
from backend.Transcription.service import transcribe_audio
from backend.auth.role_checker import check_role
from backend.Transcription.TranscriptionModel import Transcription
# from pydub import AudioSegment
# from pydub.utils import mediainfo

router = APIRouter()
settings = TenantSettings()


@router.post("/upload-recording", response_model=RecordingResponse)
def upload_recording(
    background_tasks: BackgroundTasks,
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

    recording_data = {
        "id": CallRecoding.id,
        "staff_id": CallRecoding.staff_id,
        "start_time": CallRecoding.start_time,
        "end_time": CallRecoding.end_time,
        "call_duration": CallRecoding.call_duration,
        "audio_length": CallRecoding.audio_length,
        "file_url": CallRecoding.file_url,
    }
    if(CallRecoding.call_duration > 300):
        transcribe_audio(recording_data["id"], db)

    return RecordingResponse(**recording_data)


@router.get("/get-recordings", response_model=List[GetRecording])
def get_recordings(
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timeline: Optional[str] = Query(None, description="Timeline e.g. Last 7 days, Last 30 days, Previous month, Last 90 days, Last 365 days, All time"),
    store_id: Optional[str] = None,
    regional_id: Optional[str] = None,
    state_id: Optional[str] = None,
    city_id: Optional[str] = None,
):
    user_id = token.get("user_id")
    user_role_str = token.get("role")

    try:
        user_role = RoleEnum(user_role_str)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid user role.")

    # Use timeline to override start and end date if they are not manually provided
    if not start_date and not end_date:
        start_date_obj, end_date_obj = parse_timeline(timeline)
    else:
        start_date_obj, end_date_obj = parse_dates(start_date, end_date)

    # Determine downline users based on role and filters
    users = []

    if city_id:
        l1_users = db.query(L1).filter(L1.L1_id == city_id).all()
        users = [u for l1 in l1_users for u in extract_users(l1.user_id, RoleEnum.L1, db)]
    elif state_id:
        l3_users = db.query(L3).filter(L3.L3_id == state_id).all()
        users = [u for l3 in l3_users for u in extract_users(l3.user_id, RoleEnum.L3, db)]
    elif regional_id:
        if user_role in [RoleEnum.L0, RoleEnum.L1]:
            raise HTTPException(status_code=403, detail="L0 and L1 users cannot filter by regional ID.")
        elif user_role == RoleEnum.L2:
            l2_region = db.query(L2).filter(L2.L2_id == regional_id).first()
            if not l2_region or l2_region.user_id != user_id:
                raise HTTPException(status_code=403, detail="L2 users can only access their own region.")
            regional_user_id = l2_region.user_id
        else:
            l2_region = db.query(L2).filter(L2.L2_id == regional_id).first()
            if not l2_region:
                raise HTTPException(status_code=404, detail="Invalid regional ID provided.")
            regional_user_id = l2_region.user_id

        users = extract_users(regional_user_id, RoleEnum.L2, db)
    else:
        users = extract_users(user_id, user_role, db)

    downline_user_ids = [u.user_id for u in users if u]

    # Get recordings
    recordings = extract_recordings(
        db, user_id, user_role,
        start_date=start_date_obj,
        end_date=end_date_obj,
        store_id=store_id,
        user_ids=downline_user_ids
    )

    # Get transcriptions for these recordings
    recording_ids = [rec.id for rec in recordings]
    transcriptions = {}
    if recording_ids:
        transcription_records = db.query(Transcription).filter(
            Transcription.audio_id.in_(recording_ids)
        ).all()
        for trans in transcription_records:
            transcriptions[trans.audio_id] = {
                "id": trans.id,
                "text": trans.transcription_text
            }

    # Prepare response
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
            transcription_status=rec.transcription_status or TransctriptionStatus.pending,
            transcription_text=transcriptions.get(rec.id, {}).get("text"),
            transcription_id=transcriptions.get(rec.id, {}).get("id")
        )
        for rec in recordings
    ]

def parse_timeline(timeline: str):
    today = date.today()

    if timeline == "Last 7 days":
        start = today - timedelta(days=6)
        end = today

    elif timeline == "Last 30 days":
        start = today - timedelta(days=29)
        end = today

    elif timeline == "Previous month":
        first_day_this_month = today.replace(day=1)
        last_day_previous_month = first_day_this_month - timedelta(days=1)
        start = last_day_previous_month.replace(day=1)
        end = last_day_previous_month

    elif timeline == "Last 90 days":
        start = today - timedelta(days=89)
        end = today

    elif timeline == "Last 365 days":
        start = today - timedelta(days=364)
        end = today

    elif timeline == "All time":
        start = date(2000, 1, 1)
        end = today

    else:
        raise ValueError(f"Unsupported timeline: {timeline}")

    start_datetime = datetime.combine(start, datetime.min.time())
    end_datetime = datetime.combine(end, datetime.max.time())
    return start_datetime, end_datetime

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
            raise HTTPException(
                status_code=400, detail="Start date must be before end date"
            )

        return start_date_obj, end_date_obj
    except ValueError:
        raise HTTPException(
            status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
        )

@router.get("/get-last-recording", response_model=GetLastRecording)
@check_role([RoleEnum.L1, RoleEnum.L2, RoleEnum.L3, RoleEnum.L4])
def get_last_recording(
    user_id: Optional[str] = Query(None, description="User ID to fetch the last recording for"),
    regional_id: Optional[str] = Query(None, description="Filter by regional (L2) ID"),
    state_id: Optional[str] = Query(None, description="Filter by state (L3) ID"),
    city_id: Optional[str] = Query(None, description="Filter by city (L1) ID"),
    timeline: Optional[str] = Query(None, description="Timeline e.g. Last 7 days, Last 30 days,Previous month,Last 90 days,Last 365 days,All time"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
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
            raise HTTPException(status_code=403, detail="Invalid user role")

        # Determine user scope
        users = []

        if user_id:
            users = [db.query(User).filter(User.user_id == user_id).first()]
        elif regional_id:
            l2 = db.query(L2).filter(L2.L2_id == regional_id).first()
            if not l2:
                raise HTTPException(status_code=404, detail="Region not found")
            users = extract_users(l2.user_id, RoleEnum.L2, db)
        elif city_id:
            l1 = db.query(L1).filter(L1.L1_id == city_id).first()
            if not l1:
                raise HTTPException(status_code=404, detail="City not found")
            users = extract_users(l1.user_id, RoleEnum.L1, db)
        elif state_id:
            l3 = db.query(L3).filter(L3.L3_id == state_id).first()
            if not l3:
                raise HTTPException(status_code=404, detail="State not found")
            users = extract_users(l3.user_id, RoleEnum.L3, db)
        else:
            users = extract_users(token_user_id, user_role, db)

        user_ids = [u.user_id for u in users if u]

        # Date filtering
        if timeline:
            start_date_obj, end_date_obj = parse_timeline(timeline)
        else:
            if not start_date:
                start_date_obj = datetime(2000, 1, 1)
            else:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")

            if not end_date:
                end_date_obj = datetime.utcnow()
            else:
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
                end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)

        query = (
            db.query(
                VoiceRecording,
                L0.L0_name.label("store_name"),
                User.name.label("asm_name")
            )
            .join(User, VoiceRecording.user_id == User.user_id)
            .outerjoin(L0, VoiceRecording.store_id == L0.L0_id)
            .filter(
                VoiceRecording.user_id.in_(user_ids),
                VoiceRecording.created_at >= start_date_obj,
                VoiceRecording.created_at <= end_date_obj
            )
            .order_by(VoiceRecording.created_at.desc())
        )

        last_recording = query.first()

        if not last_recording:
            raise HTTPException(status_code=404, detail="No recordings found")

        rec = last_recording.VoiceRecording

        return GetLastRecording(
            recording_id=rec.id,
            user_id=rec.user_id,
            start_time=rec.start_time,
            end_time=rec.end_time,
            call_duration=rec.call_duration,
            audio_length=rec.audio_length,
            listening_time=rec.listening_time or 0.0,
            file_url=rec.file_url,
            store_name=last_recording.store_name or "Unknown",
            asm_name=last_recording.asm_name or "Unknown",
            created_at=rec.created_at,
            modified_at=rec.modified_at,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching last recording: {e}"
        )


@router.get("/get-daily-recording-hours", response_model=dict)
def get_daily_recording_hours(
    timeline: Optional[str] = Query("Last 7 days", description="Timeline e.g. Last 7 days, Last 30 days, Previous month, Last 90 days, Last 365 days, All time"),
    user_id: Optional[str] = Query(None, description="User ID to fetch recording hours for"),
    regional_id: Optional[str] = Query(None, description="Optional Region (L2) ID"),
    state_id: Optional[str] = Query(None, description="Optional State (L3) ID"),
    city_id: Optional[str] = Query(None, description="Optional City (L1) ID"),
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

        # Determine target users based on filters
        users = []

        if user_id:
            users = [db.query(User).filter(User.user_id == user_id).first()]
        elif city_id:
            l1_users = db.query(L1).filter(L1.L1_id == city_id).all()
            users = [u for l1 in l1_users for u in extract_users(l1.user_id, RoleEnum.L1, db)]
        elif state_id:
            l3_users = db.query(L3).filter(L3.L3_id == state_id).all()
            users = [u for l3 in l3_users for u in extract_users(l3.user_id, RoleEnum.L3, db)]
        elif regional_id:
            l2 = db.query(L2).filter(L2.L2_id == regional_id).first()
            if not l2:
                raise HTTPException(status_code=404, detail="Region not found.")
            users = extract_users(l2.user_id, RoleEnum.L2, db)
        else:
            users = extract_users(token_user_id, user_role, db)

        user_ids = [u.user_id for u in users if u]

        start_date, end_date = parse_timeline(timeline)

        daily_hours = (
            db.query(
                cast(VoiceRecording.start_time, Date).label("recording_date"),
                func.sum(VoiceRecording.call_duration).label("total_duration"),
            )
            .filter(VoiceRecording.user_id.in_(user_ids))
            .filter(VoiceRecording.start_time >= start_date)
            .filter(VoiceRecording.start_time <= end_date + timedelta(days=1))
            .group_by(cast(VoiceRecording.start_time, Date))
            .order_by("recording_date")
            .all()
        )

        if not daily_hours:
            raise HTTPException(status_code=404, detail="No recordings found")

        return {
            "user_id": user_id or token_user_id,
            "timeline": timeline,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "daily_recording_hours": {
                record.recording_date.isoformat(): round(record.total_duration / 3600, 2)
                for record in daily_hours
            },
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching daily recording hours: {str(e)}")


@router.get("/recordings-insights", response_model=dict)
@check_role([RoleEnum.L1, RoleEnum.L2, RoleEnum.L3, RoleEnum.L4])
def get_recordings_insights(
    user_id: Optional[str] = Query(None, description="User ID to fetch insights for"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    regional_id: Optional[str] = Query(None, description="Regional ID (L2 ID)"),
    state_id: Optional[str] = Query(None, description="State ID (L3 ID)"),
    city_id: Optional[str] = Query(None, description="City ID (L1 ID)"),
    timeline: Optional[str] = Query(None, description="Timeline e.g. Last 7 days, Last 30 days,Previous month,Last 90 days,Last 365 days, All time"),
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

        # Parse date range
        if timeline and (start_date or end_date):
            raise HTTPException(status_code=400, detail="Provide either timeline or start/end date, not both.")
        if timeline:
            start_date_obj, end_date_obj = parse_timeline(timeline)
        else:
            start_date_obj, end_date_obj = parse_dates(start_date, end_date)

        user_reports = None

        # Priority: city_id > state_id > regional_id
        if city_id:
            city = db.query(L1).filter(L1.L1_id == city_id).first()
            if not city:
                raise HTTPException(status_code=404, detail="Invalid city_id")
            city_user_id = city.user_id
            user_reports = extract_users(city_user_id, RoleEnum.L1, db)

        elif state_id:
            state = db.query(L3).filter(L3.L3_id == state_id).first()
            if not state:
                raise HTTPException(status_code=404, detail="Invalid state_id")
            state_user_id = state.user_id
            user_reports = extract_users(state_user_id, RoleEnum.L3, db)

        elif regional_id:
            if user_role in [RoleEnum.L0, RoleEnum.L1]:
                raise HTTPException(status_code=403, detail="L0 and L1 users cannot filter by regional ID.")
            l2 = db.query(L2).filter(L2.L2_id == regional_id).first()
            if not l2:
                raise HTTPException(status_code=404, detail="Invalid regional ID provided.")
            if user_role == RoleEnum.L2 and l2.user_id != token_user_id:
                raise HTTPException(status_code=403, detail="L2 users can only access their own region.")
            regional_user_id = l2.user_id
            user_reports = extract_users(regional_user_id, RoleEnum.L2, db)

        else:
            user_reports = extract_users(token_user_id, user_role, db)

        # Filter down if user_id is specifically provided
        if user_id:
            allowed_user_ids = {user.user_id for user in user_reports}
            if user_id not in allowed_user_ids:
                raise HTTPException(status_code=403, detail="You don't have permission to access this user's insights.")
            user_ids = [user_id]
        else:
            user_ids = [user.user_id for user in user_reports]

        filters = [
            VoiceRecording.user_id.in_(user_ids),
            VoiceRecording.created_at >= start_date_obj,
            VoiceRecording.created_at <= end_date_obj,
        ]

        # === Insights calculation ===
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
        peak_hours = {int(r.hour_of_day): r.call_count for r in hourly_counts}

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
