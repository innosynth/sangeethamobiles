import boto3
from botocore.client import Config
from backend.config import TenantSettings
from backend.AudioProcessing.utils import file_storage
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from datetime import datetime
import json
import os

settings = TenantSettings()


def upload_recording(
    Recording, staff_id, start_time, end_time, CallDuration, db, token
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
        call_duration=CallDuration,
    )

    # Add to the session and commit the transaction
    db.add(new_call_recording)
    db.commit()
    return new_call_recording
