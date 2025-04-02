from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.Feedback.FeedbackModel import FeedbackModel
from backend.Feedback.FeedbackSchema import Feedback
from backend.User.UserModel import Staff
from backend.User.service import extract_users


def extract_feedbacks(db, user_id, role, start_date, end_date, store_id=None):
    users = extract_users(user_id, role, db)  # Role-based filtering
    user_ids = [user.user_id for user in users]  # Extract user IDs efficiently

    # Build base query
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
            FeedbackModel.user_id.in_(user_ids),
            FeedbackModel.created_at >= start_date,
            FeedbackModel.created_at <= end_date,
        )
        .order_by(FeedbackModel.created_at.desc())
    )

    if store_id:  # ✅ Apply store filter via VoiceRecording table
        query = query.filter(VoiceRecording.store_id == store_id)

    feedbacks = query.all()

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
