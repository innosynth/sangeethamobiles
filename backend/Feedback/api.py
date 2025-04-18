from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from backend.Area.AreaModel import L1
from backend.AudioProcessing.api import parse_dates, parse_timeline
from backend.State.stateModel import L3
from backend.User.service import extract_users
from backend.auth.jwt_handler import verify_token
from backend.db.db import get_session
from backend.Feedback.FeedbackModel import FeedbackModel
from backend.Feedback.FeedbackSchema import FeedbackCreate, FeedbackResponse, Feedback
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.User.UserModel import Staff
import uuid
from typing import Optional
import json
from datetime import datetime, timedelta
from backend.User.UserModel import User
from backend.Feedback.service import extract_feedbacks
from backend.sales.SalesModel import L2
from backend.schemas.RoleSchema import RoleEnum

router = APIRouter()


@router.post("/feedback", response_model=FeedbackResponse)
def create_feedback(
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        # Authentication check
        user_id = token.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Unauthorized")

        # Check if audio_id already exists
        existing_audio = (
            db.query(FeedbackModel)
            .filter(FeedbackModel.audio_id == feedback_data.audio_id)
            .first()
        )
        if existing_audio:
            raise HTTPException(
                status_code=400,
                detail="This audio recording already has feedback submitted",
            )

        # Check voice recording exists
        voice_recording = (
            db.query(VoiceRecording)
            .filter(
                VoiceRecording.user_id == user_id,
                VoiceRecording.staff_id == feedback_data.staff_id,
            )
            .first()
        )
        if not voice_recording:
            raise HTTPException(status_code=404, detail="Voice recording not found")

        # Get staff details
        staff = db.query(Staff).filter(Staff.id == feedback_data.staff_id).first()
        if not staff:
            raise HTTPException(status_code=404, detail="Staff member not found")

        # Check if feedback is already a dict (no need to json.loads)
        if isinstance(feedback_data.feedback, dict):
            feedback_json = feedback_data.feedback
        else:
            try:
                feedback_json = json.loads(feedback_data.feedback)
            except (json.JSONDecodeError, TypeError):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid feedback format - must be valid JSON",
                )

        contact_number = feedback_data.number

        # If contact number exists, check for recent submissions
        if contact_number:
            forty_eight_hours_ago = datetime.utcnow() - timedelta(hours=48)
            recent_feedback = (
                db.query(FeedbackModel)
                .filter(
                    FeedbackModel.user_id == user_id,
                    FeedbackModel.created_at > forty_eight_hours_ago,
                    FeedbackModel.feedback.like(
                        f'%"contact_number":"{contact_number}"%'
                    ),
                )
                .first()
            )

            if recent_feedback:
                raise HTTPException(
                    status_code=400,
                    detail="Feedback with this contact number was submitted recently (within 48 hours)",
                )

        # Create new feedback - ensure we store as JSON string
        feedback = FeedbackModel(
            id=str(uuid.uuid4()),
            audio_id=feedback_data.audio_id,
            user_id=user_id,
            created_by=feedback_data.staff_id,
            feedback=(
                json.dumps(feedback_json)
                if isinstance(feedback_json, dict)
                else feedback_data.feedback
            ),
            Billed=feedback_data.Billed,
            number=feedback_data.number,
        )

        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        return FeedbackResponse(
            id=feedback.id,
            user_id=user_id,
            staff_id=feedback.created_by,
            created_at=feedback.created_at,
            modified_at=feedback.modified_at,
            staff_name=staff.name,
            staff_email=staff.email_id,
            feedback=feedback.feedback,
            number=feedback.number,
            Billed=feedback.Billed,
        )

    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error creating feedback: {str(e)}"
        )


@router.get("/list-feedbacks", response_model=List[Feedback])
def get_all_feedbacks(
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
    # Authentication
    user_id = token.get("user_id")
    role_str = token.get("role")
    if not user_id or role_str is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_role = RoleEnum(role_str)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid user role.")

    # Parse date range or fallback to timeline
    try:
        if not start_date or not end_date:
            start_date_obj, end_date_obj = parse_timeline(timeline)
        else:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)

            if start_date_obj > end_date_obj:
                raise HTTPException(status_code=400, detail="Start date must be before end date")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Determine downline users based on filters
    users = []

    if city_id:
        l1_users = db.query(L1).filter(L1.L1_id == city_id).all()
        users = [u for l1 in l1_users for u in extract_users(l1.user_id, RoleEnum.L1, db)]
    elif state_id:
        l3_users = db.query(L3).filter(L3.L3_id == state_id).all()
        users = [u for l3 in l3_users for u in extract_users(l3.user_id, RoleEnum.L3, db)]
    elif regional_id:
        if user_role in [RoleEnum.L0, RoleEnum.L1]:
            raise HTTPException(status_code=403, detail="L0 and L1 users cannot use regional filter.")
        elif user_role == RoleEnum.L2:
            region = db.query(L2).filter(L2.L2_id == regional_id).first()
            if not region or region.user_id != user_id:
                raise HTTPException(status_code=403, detail="L2 users can only access their own region.")
            regional_user_id = region.user_id
        else:
            region = db.query(L2).filter(L2.L2_id == regional_id).first()
            if not region:
                raise HTTPException(status_code=404, detail="Invalid regional ID provided.")
            regional_user_id = region.user_id

        users = extract_users(regional_user_id, RoleEnum.L2, db)
    else:
        users = extract_users(user_id, user_role, db)

    user_ids = [u.user_id for u in users if u]

    # Fetch feedbacks
    feedbacks = extract_feedbacks(
        db=db,
        user_id=None,
        role=None,
        start_date=start_date_obj,
        end_date=end_date_obj,
        store_id=store_id,
        user_ids=user_ids,
    )

    if not feedbacks:
        raise HTTPException(status_code=404, detail="No feedback found for the given period")

    return feedbacks


@router.get("/feedback-rating", response_model=dict)
def get_feedback_rating(
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
    store_id: Optional[str] = None,
    regional_id: Optional[str] = None,
    state_id: Optional[str] = None,
    city_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    timeline: Optional[str] = Query(None, description="Timeline e.g. Last 7 days, Last 30 days, Previous month, Last 90 days, Last 365 days, All time")
):
    # Authentication check
    user_id = token.get("user_id")
    role_str = token.get("role")
    if not user_id or role_str is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    try:
        user_role = RoleEnum(role_str)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid role")

    # Parse date range or fallback to timeline
    try:
        if not start_date or not end_date:
            start_date_obj, end_date_obj = parse_timeline(timeline)
        else:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)

            if start_date_obj > end_date_obj:
                raise HTTPException(status_code=400, detail="Start date must be before end date")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    # Determine downline users based on filters
    users = []

    if city_id:
        l1_users = db.query(L1).filter(L1.L1_id == city_id).all()
        users = [u for l1 in l1_users for u in extract_users(l1.user_id, RoleEnum.L1, db)]
    elif state_id:
        l3_users = db.query(L3).filter(L3.L3_id == state_id).all()
        users = [u for l3 in l3_users for u in extract_users(l3.user_id, RoleEnum.L3, db)]
    elif regional_id:
        if user_role in [RoleEnum.L0, RoleEnum.L1]:
            raise HTTPException(status_code=403, detail="L0 and L1 users cannot use regional filter.")
        elif user_role == RoleEnum.L2:
            region = db.query(L2).filter(L2.L2_id == regional_id).first()
            if not region or region.user_id != user_id:
                raise HTTPException(status_code=403, detail="L2 users can only access their own region.")
            regional_user_id = region.user_id
        else:
            region = db.query(L2).filter(L2.L2_id == regional_id).first()
            if not region:
                raise HTTPException(status_code=404, detail="Invalid regional ID provided.")
            regional_user_id = region.user_id

        users = extract_users(regional_user_id, RoleEnum.L2, db)
    else:
        users = extract_users(user_id, user_role, db)

    user_ids = [u.user_id for u in users]

    # Fetch voice recordings
    query = db.query(VoiceRecording).filter(
        VoiceRecording.user_id.in_(user_ids),
        VoiceRecording.created_at >= start_date_obj,
        VoiceRecording.created_at <= end_date_obj,
    )

    if store_id:
        query = query.filter(VoiceRecording.store_id == store_id)

    voice_recordings = query.all()

    if not voice_recordings:
        return {
            "requested_by": user_id if user_role != RoleEnum.L4 else "Super Admin",
            "total_feedbacks": 0,
            "positive_feedbacks": 0,
            "negative_feedbacks": 0,
            "average_feedbacks": 0,
        }

    audio_ids = [rec.id for rec in voice_recordings]
    feedbacks = db.query(FeedbackModel).filter(
        FeedbackModel.audio_id.in_(audio_ids),
        FeedbackModel.created_at >= start_date_obj,
        FeedbackModel.created_at <= end_date_obj,
    ).all()

    positive_feedbacks = negative_feedbacks = average_feedbacks = 0

    for feedback in feedbacks:
        try:
            feedback_data = json.loads(feedback.feedback)
            call_rating = feedback_data.get("callRating", "").lower()
            if call_rating == "good":
                positive_feedbacks += 1
            elif call_rating == "bad":
                negative_feedbacks += 1
            elif call_rating == "average":
                average_feedbacks += 1
        except json.JSONDecodeError:
            continue

    return {
        "requested_by": user_id if user_role != RoleEnum.L4 else "Super Admin",
        "total_feedbacks": len(feedbacks),
        "positive_feedbacks": positive_feedbacks,
        "negative_feedbacks": negative_feedbacks,
        "average_feedbacks": average_feedbacks,
    }
