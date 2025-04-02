import boto3
from botocore.client import Config
from backend.config import TenantSettings
from backend.AudioProcessing.utils import file_storage
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from datetime import datetime
import io
import os
from backend.Store.StoreModel import L0
from backend.User.service import extract_users
from backend.User.UserModel import User

settings = TenantSettings()

from pydub import AudioSegment
from pydub.utils import mediainfo


def upload_recording(
    Recording, staff_id, start_time, end_time, CallDuration, store_id, db, token
):
    affilated_user_id = token.get("user_id")
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
    store_fname = Recording.filename
    f_name, *etn = store_fname.split(".")
    file_path, file_exe = file_storage(Recording, f_name)
    file_size = round(os.path.getsize(file_path) / (1024 * 1024), 2)
    if CallDuration == None:
        duration = end_time - start_time
        CallDuration = duration.total_seconds()
    with open(file_path, "rb") as data:
        current_datetime = datetime.now()
        formatted_datetime = (
            current_datetime.strftime("%Y%m%d%H%M%S%f") + "." + str(etn[0])
        )
        upload = client_s3.upload_fileobj(
            data,
            S3_bucket_name,
            f"{str(affilated_user_id)}/{formatted_datetime}",
            ExtraArgs={"ContentType": "audio/mp3"},
        )
    url = f"{S3_CDN}/{str(affilated_user_id)}/{formatted_datetime}"

    new_call_recording = VoiceRecording(
        user_id=affilated_user_id,
        staff_id=staff_id,
        audio_length=file_size,
        file_url=url,
        start_time=start_time,
        end_time=end_time,
        store_id=store_id,
        call_duration=CallDuration,
    )

    # Add to the session and commit the transaction
    db.add(new_call_recording)
    db.commit()
    return new_call_recording


def extract_recordings(db, user_id, user_role, start_date, end_date, store_id=None):
    users = extract_users(user_id, user_role, db)
    user_ids = [user.user_id for user in users]
    query = db.query(VoiceRecording).filter(
        VoiceRecording.user_id.in_(user_ids),
        VoiceRecording.created_at >= start_date,
        VoiceRecording.created_at <= end_date,
    )

    if store_id:
        query = query.filter(VoiceRecording.store_id == store_id)
    recordings = query.all()
    store_ids = {rec.store_id for rec in recordings if rec.store_id}

    if store_ids:
        store_info = (
            db.query(
                L0.L0_id.label("store_id"),
                L0.L0_name.label("store_name"),
                L0.L0_code.label("store_code"),
                L0.L0_addr.label("store_address"),
                User.name.label("asm_name"),
            )
            .outerjoin(User, L0.user_id == User.user_id)
            .filter(L0.L0_id.in_(store_ids))
            .all()
        )

        store_data = {
            store.store_id: {
                "store_name": store.store_name,
                "store_code": store.store_code,
                "store_address": store.store_address,
                "asm_name": store.asm_name or "Unknown",
            }
            for store in store_info
        }
    else:
        store_data = {}

    for rec in recordings:
        store = store_data.get(
            rec.store_id,
            {
                "store_name": "Unknown",
                "store_code": "Unknown",
                "store_address": "Unknown",
                "asm_name": "Unknown",
            },
        )

        rec.store_name = store["store_name"]
        rec.store_code = store["store_code"]
        rec.store_address = store["store_address"]
        rec.asm_name = store["asm_name"]

    return recordings
