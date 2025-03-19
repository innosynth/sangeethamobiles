from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from backend.auth.jwt_handler import verify_token
from backend.db.db import get_session
from backend.Feedback.FeedbackModel import FeedbackModel
from backend.Feedback.FeedbackSchema import FeedbackCreate, FeedbackResponse
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
import uuid
import json
from datetime import datetime

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
    )


@router.get("/list-feedbacks", response_model=List[FeedbackResponse])
def get_all_feedbacks(
    db: Session = Depends(get_session), token: dict = Depends(verify_token)
):
    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    feedbacks = db.query(FeedbackModel).filter().all()

    if not feedbacks:
        raise HTTPException(status_code=404, detail="No feedback found for this user")

    feedback_list = [
        FeedbackResponse(
            id=feedback.id,
            user_id=user_id,
            staff_id=feedback.created_by,  # Assuming created_by stores staff_id
            feedback=feedback.feedback,  # Ensure feedback is parsed
            created_at=feedback.created_at,
            modified_at=feedback.modified_at,
        )
        for feedback in feedbacks
    ]
    return feedback_list


@router.get("/feedback/{feedback_id}", response_model=FeedbackResponse)
def get_feedback(
    feedback_id: str,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

    feedback = db.query(FeedbackModel).filter(FeedbackModel.id == feedback_id).first()
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    # parsed_feedback = json.loads(feedback.feedback)

    return FeedbackResponse(
        id=feedback.id,
        user_id=user_id,
        staff_id=feedback.created_by,  # Assuming created_by is staff_id
        feedback=feedback.feedback,
        created_at=feedback.created_at,
        modified_at=feedback.modified_at,
    )
