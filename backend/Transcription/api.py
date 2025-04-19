from fastapi import HTTPException, BackgroundTasks, Query
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.AudioProcessing.api import parse_dates, parse_timeline
from backend.AudioProcessing.service import extract_recordings
from backend.Transcription.service import transcribe_audio
from backend.db.db import get_session
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.Transcription.TranscriptionModel import Transcription, TranscribeAI
from backend.schemas.TranscriptionSchema import TransctriptionStatus
from sqlalchemy import func, desc
from typing import List, Dict, Any, Optional
import json
import os
from wordcloud import WordCloud
import boto3
from botocore.client import Config
import matplotlib.pyplot as plt
from collections import Counter
from backend.User.UserModel import User
from backend.Area.AreaModel import L1
from backend.sales.SalesModel import L2
from backend.State.stateModel import L3 
from collections import Counter
from backend.auth.jwt_handler import verify_token
from backend.auth.role_checker import check_role
from backend.schemas.RoleSchema import RoleEnum
from backend.Feedback.FeedbackModel import FeedbackModel
from datetime import datetime, timedelta
from backend.User.service import extract_users
from backend.config import TenantSettings

router = APIRouter()
settings = TenantSettings()
STATIC_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
POSITIVE_WORD_CLOUD_PATH = os.path.join(STATIC_DIR, "positive_word_cloud.png")
NEGATIVE_WORD_CLOUD_PATH = os.path.join(STATIC_DIR, "negative_word_cloud.png")

os.makedirs(STATIC_DIR, exist_ok=True)

def generate_word_cloud(words, output_path, title="Word Cloud"):
    """
    Generate a word cloud from a list of words and save it to the specified path.
    """
    if not words:
        plt.figure(figsize=(10, 6))
        plt.text(0.5, 0.5, "No data available", 
                 horizontalalignment='center', 
                 verticalalignment='center',
                 fontsize=16)
        plt.axis('off')
        plt.savefig(output_path)
        plt.close()
        return
    
    wordcloud = WordCloud(
        width=800, 
        height=400, 
        background_color='white',
        max_words=100,
        contour_width=3,
        contour_color='steelblue'
    ).generate_from_frequencies(dict(Counter(words)))
    
    plt.figure(figsize=(10, 6))
    plt.imshow(wordcloud, interpolation='bilinear')
    plt.axis('off')
    plt.title(title, fontsize=16)
    
    plt.savefig(output_path)
    plt.close()
    S3_access_key = settings.S3_ACCESS_KEY
    S3_access_secret = settings.S3_SECRET_KEY
    S3_bucket_name = settings.S3_BUCKET_NAME
    S3_EndPoint = settings.S3_ENDPOINT
    S3_CDN = settings.S3_CDN

    client_s3 = boto3.client(
        "s3",
        endpoint_url=S3_EndPoint,
        aws_access_key_id=S3_access_key,
        aws_secret_access_key=S3_access_secret,
        config=Config(signature_version="s3v4", region_name="auto"),
    )
    with open(output_path, "rb") as data:
        # Ensure pointer is at the beginning
        data.seek(0)

        current_datetime = datetime.now()
        formatted_datetime = (
            current_datetime.strftime("%Y%m%d%H%M%S%f") + "." + "png")
        

        # Upload to S3
        client_s3.upload_fileobj(
            data,
            S3_bucket_name,
            f"wordcloud/{formatted_datetime}",
            ExtraArgs={"ContentType": "image/png"},
        )
    url = f"{S3_CDN}/wordcloud/{formatted_datetime}"
    return url

@router.post("/on-demnad-transcription")
@check_role([RoleEnum.L1, RoleEnum.L2, RoleEnum.L3, RoleEnum.L4])
def start_transcription(
    recording_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    user_id = token.get("user_id")
    role_str = token.get("role")

    try:
        user_role = RoleEnum(role_str)
    except ValueError:
        raise HTTPException(status_code=403, detail="Invalid user role")

    recording = db.query(VoiceRecording).filter(VoiceRecording.id == recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    # Get all allowed user_ids for the current user based on hierarchy
    allowed_users = [u.user_id for u in extract_users(user_id, user_role, db)]

    # Add self to allowed list
    allowed_users.append(user_id)

    # If the recording doesn't belong to allowed hierarchy, block it
    if recording.user_id not in allowed_users:
        raise HTTPException(status_code=403, detail="You are not authorized to transcribe this recording")

    if recording.transcription_status != TransctriptionStatus.pending:
        return {"error": "Transcription already in progress or completed"}

    transcribe_audio(recording_id, db)

    # Fetch transcription_id created in TranscribeAI for the recording
    transcribe_record = db.query(TranscribeAI).filter(TranscribeAI.audio_id == recording_id).first()

    if not transcribe_record:
        return {"error": "Transcription failed or not recorded"}

    return {
        "Status": "transcription started successfully",
        "Transcription_id": str(transcribe_record.id)
    }

@router.get("/get-transcription-analytics")
@check_role([RoleEnum.L1, RoleEnum.L2, RoleEnum.L3, RoleEnum.L4])
def get_transcription_analytics(
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    store_id: Optional[str] = None,
    regional_id: Optional[str] = None,
    state_id: Optional[str] = None,
    city_id: Optional[str] = None,
    timeline: Optional[str] = Query(None, description="Timeline e.g. Last 7 days, Last 30 days, Previous month, Last 90 days, Last 365 days, All time"),
):
    try:
        user_id = token.get("user_id")
        role_str = token.get("role")
        if not user_id or not role_str:
            raise HTTPException(status_code=401, detail="Unauthorized")
        user_role = RoleEnum(role_str)

        start_date_obj, end_date_obj = parse_dates(start_date, end_date)

        # Handle Timeline filter if provided
        if timeline:
            end_date_obj = datetime.utcnow().date()
            if timeline == "Last 7 days":
                start_date_obj = end_date_obj - timedelta(days=7)
            elif timeline == "Last 30 days":
                start_date_obj = end_date_obj - timedelta(days=30)
            elif timeline == "Last 90 days":
                start_date_obj = end_date_obj - timedelta(days=90)
            elif timeline == "Last 180 days":
                start_date_obj = end_date_obj - timedelta(days=180)
            elif timeline == "Last 365 days":
                start_date_obj = end_date_obj - timedelta(days=365)
            else:
                raise HTTPException(status_code=400, detail="Invalid timeline. Use 'Last 7 days', 'Last 30 days', etc.")

        # RBAC
        if regional_id:
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
            downline_user_ids = [u.user_id for u in extract_users(regional_user_id, RoleEnum.L2, db)]
        else:
            downline_user_ids = [u.user_id for u in extract_users(user_id, user_role, db)]

        # Filter by state_id and city_id if provided
        if state_id:
            downline_user_ids = [
                u.user_id for u in extract_users(user_id, user_role, db) if u.state_id == state_id
            ]
        if city_id:
            downline_user_ids = [
                u.user_id for u in extract_users(user_id, user_role, db) if u.city_id == city_id
            ]

        # Recordings
        recordings = extract_recordings(
            db, user_id, user_role,
            start_date=start_date_obj,
            end_date=end_date_obj,
            store_id=store_id,
            user_ids=downline_user_ids
        )
        recording_ids = [rec.id for rec in recordings]
        total_transcriptions = len(recording_ids)

        # Transcription stats
        on_demand_transcriptions = db.query(VoiceRecording).filter(
            VoiceRecording.id.in_(recording_ids),
            VoiceRecording.transcription_status == TransctriptionStatus.completed,
            VoiceRecording.call_duration < 300
        ).count()
        failed_transcriptions = db.query(VoiceRecording).filter(
            VoiceRecording.id.in_(recording_ids),
            VoiceRecording.transcription_status == TransctriptionStatus.failure
        ).count()
        pending_transcriptions = db.query(VoiceRecording).filter(
            VoiceRecording.id.in_(recording_ids),
            VoiceRecording.transcription_status == TransctriptionStatus.pending
        ).count()
        finished_transcriptions = db.query(VoiceRecording).filter(
            VoiceRecording.id.in_(recording_ids),
            VoiceRecording.transcription_status == TransctriptionStatus.completed
        ).count()

        # TranscribeAI data
        transcribe_ai_data = db.query(TranscribeAI).filter(
            TranscribeAI.audio_id.in_(recording_ids)
        ).all()

        # Counters
        emotion_counter = Counter()
        product_counter = Counter()
        complaint_counter = Counter()
        contact_reason_counter = Counter()
        category_interest_counter = Counter()
        language_counter = Counter()
        gender_counter = Counter()
        all_positive_keywords = []
        all_negative_keywords = []

        for ai in transcribe_ai_data:
            if ai.emotional_state:
                emotion_counter.update(ai.emotional_state)
            if ai.product_mentions:
                product_counter.update(ai.product_mentions)
            if ai.complaints:
                complaint_counter.update(ai.complaints)
            if ai.contact_reason:
                contact_reason_counter.update(ai.contact_reason)
            if ai.customer_interest:
                category_interest_counter.update(ai.customer_interest)
            if ai.language and ai.language != "unknown":
                language_counter.update([ai.language])
            if ai.gender and ai.gender != "unknown":
                gender_counter.update([ai.gender])
            if ai.positive_keywords:
                all_positive_keywords.extend(ai.positive_keywords)
            if ai.negative_keywords:
                all_negative_keywords.extend(ai.negative_keywords)

        def format_percent_object(counter: Counter, top_n=5) -> dict:
            if not counter:
                return {}
            top_items = counter.most_common(top_n)
            total_top = sum(v for _, v in top_items)
            if total_top == 0:
                return {}
            percentages = [(k, v, round((v / total_top) * 100)) for k, v in top_items]
            percentage_sum = sum(p for _, _, p in percentages)
            diff = 100 - percentage_sum
            if diff != 0 and percentages:
                name, count, perc = percentages[0]
                percentages[0] = (name, count, perc + diff)

            return {k: {"count": v, "percentage": p} for k, v, p in percentages}

        PositiveUrl = generate_word_cloud(all_positive_keywords, POSITIVE_WORD_CLOUD_PATH, "Positive Keywords")
        NegativeUrl = generate_word_cloud(all_negative_keywords, NEGATIVE_WORD_CLOUD_PATH, "Negative Keywords")

        # Audience Demographics
        feedback_records = db.query(FeedbackModel).filter(
            FeedbackModel.audio_id.in_(recording_ids)
        ).all()
        phone_number_counter = Counter([f.number for f in feedback_records if f.number])
        frequent_threshold = 1
        frequent_numbers = sum(1 for count in phone_number_counter.values() if count > frequent_threshold)
        new_numbers = sum(1 for count in phone_number_counter.values() if count <= frequent_threshold)
        total_numbers = frequent_numbers + new_numbers
        audience_str = (
            f"existing:{round((frequent_numbers / total_numbers) * 100)}%,new:{round((new_numbers / total_numbers) * 100)}%"
            if total_numbers > 0 else "existing:0%,new:0%"
        )

        # Gender
        total_gender = sum(gender_counter.values())
        gender_str = (
            f"male:{round((gender_counter.get('male', 0) / total_gender) * 100)}%,female:{round((gender_counter.get('female', 0) / total_gender) * 100)}%"
            if total_gender > 0 else "male:0%,female:0%"
        )

        response = {
            "Total_transcriptions": total_transcriptions,
            "On_demand_transcriptions": on_demand_transcriptions,
            "Failed_transcriptions": failed_transcriptions,
            "Pending_transcriptions": pending_transcriptions,
            "Finished_transcriptions": finished_transcriptions,
            "Top_emotions": format_percent_object(emotion_counter),
            "Top_products": format_percent_object(product_counter),
            "Top_complaints": format_percent_object(complaint_counter),
            "Languages": format_percent_object(language_counter),
            "gender": gender_str,
            "audience_demographics": audience_str,
            "Primary_contact_reasons": format_percent_object(contact_reason_counter),
            "Category_interest": format_percent_object(category_interest_counter),
            "Word_cloud_positive": PositiveUrl,
            "Word_cloud_negative": NegativeUrl,
            "Created_at": transcribe_ai_data[0].created_at if transcribe_ai_data else None,
            "Modified_at": transcribe_ai_data[0].modified_at if transcribe_ai_data else None,
        }

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transcription analytics: {str(e)}")


@router.get("/transcriptions-chart")
def get_transcriptions_chart(
    store_id: Optional[str] = Query(None, description="Store ID to filter by"),
    region_id: Optional[str] = Query(None, description="Region ID to filter by"),
    state_id: Optional[str] = Query(None, description="State ID to filter by"),
    city_id: Optional[str] = Query(None, description="City ID to filter by"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    timeline: Optional[str] = Query(None, description="Timeline e.g. Last 7 days, Last 30 days, Previous month, Last 90 days, Last 365 days, All time"),
    db: Session = Depends(get_session),
    token: dict = Depends(verify_token),
):
    try:
        user_id = token.get("user_id")
        role_str = token.get("role")

        if not user_id or not role_str:
            raise HTTPException(status_code=401, detail="Unauthorized")

        try:
            user_role = RoleEnum(role_str)
        except ValueError:
            raise HTTPException(status_code=403, detail="Invalid user role")

        current_user = db.query(User).filter(User.user_id == user_id).first()
        if not current_user:
            raise HTTPException(status_code=404, detail="User not found")

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
        elif region_id:
            if user_role in [RoleEnum.L0, RoleEnum.L1]:
                raise HTTPException(status_code=403, detail="L0 and L1 users cannot filter by regional ID.")
            l2_region = db.query(L2).filter(L2.L2_id == region_id).first()
            if not l2_region:
                raise HTTPException(status_code=404, detail="Invalid regional ID provided.")
            if user_role == RoleEnum.L2 and l2_region.user_id != user_id:
                raise HTTPException(status_code=403, detail="L2 users can only access their own region.")
            regional_user_id = l2_region.user_id
            users = extract_users(regional_user_id, RoleEnum.L2, db)
        else:
            users = extract_users(user_id, user_role, db)

        user_ids = [u.user_id for u in users]
        user_ids.append(user_id)

        # Query voice recordings for those user IDs
        base_query = db.query(VoiceRecording).filter(
            VoiceRecording.user_id.in_(user_ids),
            VoiceRecording.created_at >= start_date_obj,
            VoiceRecording.created_at <= end_date_obj
        )

        if store_id:
            base_query = base_query.filter(VoiceRecording.store_id == store_id)

        recordings = base_query.all()
        recording_ids = [rec.id for rec in recordings]

        transcriptions = db.query(Transcription).filter(
            Transcription.audio_id.in_(recording_ids)
        ).all()

        # Prepare daily counts dictionary
        daily_counts = {}
        current_date = start_date_obj.date()
        end_date = end_date_obj.date()
        while current_date <= end_date:
            daily_counts[current_date.isoformat()] = 0
            current_date += timedelta(days=1)

        for trans in transcriptions:
            recording = next((rec for rec in recordings if rec.id == trans.audio_id), None)
            if recording:
                date_str = recording.created_at.date().isoformat()
                if date_str in daily_counts:
                    daily_counts[date_str] += 1

        return daily_counts

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching transcriptions chart: {str(e)}")
