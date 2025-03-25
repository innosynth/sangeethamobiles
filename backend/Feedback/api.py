from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.auth.jwt_handler import verify_token
from backend.db.db import get_session
from backend.Feedback.FeedbackModel import FeedbackModel
from backend.Feedback.FeedbackSchema import FeedbackCreate, FeedbackResponse
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.User.UserModel import Staff
import uuid
import json
from datetime import datetime
from backend.User.UserModel import User

router = APIRouter()
@router.post("/feedback", response_model=FeedbackResponse)
def create_feedback(
    feedback_data: FeedbackCreate,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Check if voice recording exists
    voice_recording = (
        db.query(VoiceRecording)
        .filter(
            VoiceRecording.user_id == user_id,
            VoiceRecording.staff_id == feedback_data.staff_id,
        )
        .first()
    )

    if not voice_recording:
        raise HTTPException(status_code=404, detail="Voice recording record not found")
    
    # Get staff details
    staff = db.query(Staff).filter(Staff.id == feedback_data.staff_id).first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    # Create feedback
    feedback = FeedbackModel(
        id=str(uuid.uuid4()),
        audio_id=feedback_data.audio_id,
        created_by=feedback_data.staff_id,
        feedback=json.dumps(feedback_data.feedback),
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

@router.get("/list-feedbacks", response_model=List[FeedbackResponse])
def get_all_feedbacks(
    db: Session = Depends(get_session), 
    token: dict = Depends(verify_token)
):
    
    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    results = (
        db.query(FeedbackModel, User)
        .join(User, User.id == FeedbackModel.created_by)
        .all()
    )
    if not results:
        raise HTTPException(status_code=404, detail="No feedback found")

    feedback_list = []
    for feedback, staff in results:
        feedback_list.append(
            FeedbackResponse(
                id=feedback.id,
                user_id=user_id,
                staff_id=staff.id,
                staff_name=staff.name,
                staff_email=staff.email,
                feedback=feedback.feedback,
                number=feedback.number,
                Billed=feedback.Billed,
                created_at=feedback.created_at,
                modified_at=feedback.modified_at,
            )
        )
    return feedback_list


@router.get("/feedback-rating", response_model=dict)
def get_feedback_rating(
    db: Session = Depends(get_session), token: dict = Depends(verify_token)
):
    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Fetch all voice recordings for the user
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
            feedback_data = json.loads(feedback.feedback) 
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
        "user_id": user_id,
        "total_feedbacks": total_feedbacks,
        "positive_feedbacks": positive_feedbacks,
        "negative_feedbacks": negative_feedbacks,
        "average_feedbacks": average_feedbacks,
    }
