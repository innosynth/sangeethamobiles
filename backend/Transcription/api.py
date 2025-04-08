from fastapi import HTTPException, BackgroundTasks
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.Transcription.service import transcribe_audio
from backend.db.db import get_session
from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording

router = APIRouter()


@router.post("/on-demnad-transcription")
def start_transcription(
    recording_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_session)
):
    recording = (
        db.query(VoiceRecording).filter(VoiceRecording.id == recording_id).first()
    )
    if not recording:
        return {"error": "Recording not found"}
    background_tasks.add_task(transcribe_audio, recording_id, db)
    return {"message": "Transcription started"}
