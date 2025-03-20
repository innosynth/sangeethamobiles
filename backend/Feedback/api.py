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
        feedback=feedback.feedback,
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


@router.get("/feedback-rating", response_model=dict)
def get_feedback_rating(
    db: Session = Depends(get_session), token: dict = Depends(verify_token)
):
    user_id = token.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Unauthorized")

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
        # print("Raw Feedback from DB:", feedback.feedback)
        try:
            feedback_data = json.loads(feedback.feedback)
            # print("Parsed Feedback:", feedback_data)
        except json.JSONDecodeError:
            # print("JSON Decode Error! Skipping feedback.")
            continue

        feedback_text = json.dumps(feedback_data).lower()

        if "good" in feedback_text:
            positive_feedbacks += 1
        elif "bad" in feedback_text:
            negative_feedbacks += 1
        elif "average" in feedback_text:
            average_feedbacks += 1

    # if positive_feedbacks > negative_feedbacks and positive_feedbacks > average_feedbacks:
    #     overall_rating = "Good"
    # elif negative_feedbacks > positive_feedbacks and negative_feedbacks > average_feedbacks:
    #     overall_rating = "Bad"
    # elif average_feedbacks > positive_feedbacks and average_feedbacks > negative_feedbacks:
    #     overall_rating = "Average"
    # else:# If there is a tie, prioritize positive > average > negative
    #     if positive_feedbacks == max(positive_feedbacks, negative_feedbacks, average_feedbacks):
    #         overall_rating = "Good"
    #     elif average_feedbacks == max(positive_feedbacks, negative_feedbacks, average_feedbacks):
    #         overall_rating = "Average"
    #     else:
    #         overall_rating = "Bad"

    return {
        "user_id": user_id,
        "total_feedbacks": total_feedbacks,
        "positive_feedbacks": positive_feedbacks,
        "negative_feedbacks": negative_feedbacks,
        "average_feedbacks": average_feedbacks,
    }
