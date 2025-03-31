from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
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
):
    try:
        # Authentication check
        user_id = token.get("user_id")
        role = token.get("role")
        if not user_id or role is None:
            raise HTTPException(status_code=401, detail="Unauthorized")

        if not start_date or not end_date:
            end_date_obj = datetime.utcnow()
            start_date_obj = end_date_obj - timedelta(days=30)
        else:
            try:
                start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
                end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")

                if start_date_obj.date() == end_date_obj.date():
                    end_date_obj = end_date_obj.replace(hour=23, minute=59, second=59)
            except ValueError:
                raise HTTPException(
                    status_code=400, detail="Invalid date format. Use YYYY-MM-DD"
                )

        if start_date_obj > end_date_obj:
            raise HTTPException(
                status_code=400, detail="Start date must be before end date"
            )

        query = (
            db.query(
                FeedbackModel,
                Staff.name.label("staff_name"),
                Staff.email_id.label("staff_email"),
                VoiceRecording.file_url.label("audio_url"),
            )
            .join(Staff, Staff.id == FeedbackModel.created_by)
            .join(VoiceRecording, VoiceRecording.id == FeedbackModel.audio_id)
            .filter(
                FeedbackModel.created_at >= start_date_obj,
                FeedbackModel.created_at <= end_date_obj,
            )
        )

        if role < 4:
            query = query.filter(FeedbackModel.user_id == user_id)

        feedbacks = query.order_by(FeedbackModel.created_at.desc()).all()
        if not feedbacks:
            raise HTTPException(
                status_code=404, detail="No feedback found for the given period"
            )

        return [
            Feedback(
                id=feedback.id,
                user_id=feedback.user_id,
                staff_id=feedback.created_by,
                staff_name=staff_name,
                staff_email=staff_email,
                feedback=feedback.feedback,
                number=feedback.number,
                Billed=feedback.Billed,
                created_at=feedback.created_at,
                modified_at=feedback.modified_at,
                audio_url=audio_url,
            )
            for feedback, staff_name, staff_email, audio_url in feedbacks
        ]

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching feedbacks: {str(e)}"
        )


@router.get("/feedback-rating", response_model=dict)
def get_feedback_rating(
    db: Session = Depends(get_session), token: dict = Depends(verify_token)
):
    user_id = token.get("user_id")
    role = token.get("role")  # Extract role from the token

    if not user_id or role is None:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Query voice recordings based on role
    if role == 4:
        voice_recordings = db.query(VoiceRecording).all()  # Fetch all voice recordings
    else:
        voice_recordings = (
            db.query(VoiceRecording).filter(VoiceRecording.user_id == user_id).all()
        )

    if not voice_recordings:
        raise HTTPException(status_code=404, detail="No voice recordings found")

    audio_ids = [record.id for record in voice_recordings]

    feedbacks = (
        db.query(FeedbackModel).filter(FeedbackModel.audio_id.in_(audio_ids)).all()
    )

    total_feedbacks = len(feedbacks)
    positive_feedbacks = 0
    negative_feedbacks = 0
    average_feedbacks = 0

    for feedback in feedbacks:
        try:
            feedback_data = json.loads(feedback.feedback)  # Convert JSON feedback
            call_rating = feedback_data.get("callRating", "").lower()
            # Categorize callRating
            if call_rating == "good":
                positive_feedbacks += 1
            elif call_rating == "bad":
                negative_feedbacks += 1
            elif call_rating == "average":
                average_feedbacks += 1

        except json.JSONDecodeError:
            continue  # Skip invalid JSON feedback entries

    return {
        "user_id": user_id if role < 4 else "Super Admin",
        "total_feedbacks": total_feedbacks,
        "positive_feedbacks": positive_feedbacks,
        "negative_feedbacks": negative_feedbacks,
        "average_feedbacks": average_feedbacks,
    }
