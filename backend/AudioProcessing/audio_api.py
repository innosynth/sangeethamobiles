from fastapi import APIRouter
import uuid
from sqlalchemy import DateTime
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from db.db import get_session
from AudioProcessing.VoiceRecordingModel import VoiceRecording
# from backend.dependencies import get_session, get_current_user  # Assuming these dependencies exist

router = APIRouter()

@router.post("/upload-recording")
def upload_recording(
    file_url: str,
    audio_length: float,
    start_time: DateTime,
    end_time: DateTime,
    call_duration: float,
    db: Session = Depends(get_session),
    user: dict = Depends(get_current_user)
):
    """ Upload a new voice recording. """
    new_recording = VoiceRecording(
        user_id=get_current_user["id"],  # Extracted from authentication
        file_url=file_url,
        audio_length=audio_length,
        start_time=start_time,
        end_time=end_time,
        call_duration=call_duration
    )
    db.add(new_recording)
    db.commit()
    db.refresh(new_recording)
    return {"message": "Recording uploaded", "recording_id": new_recording.id}

@router.get("/recordings")
def get_recordings(db: Session = Depends(get_session)):
    """ Get all recordings. """
    recordings = db.query(VoiceRecording).all()
    return {"recordings": recordings}

@router.get("/recordings/{recording_id}")
def get_recording(recording_id: str, db: Session = Depends(get_session)):
    """ Get a specific recording by ID. """
    recording = db.query(VoiceRecording).filter_by(id=recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording

@router.delete("/recordings/{recording_id}")
def delete_recording(recording_id: str, db: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    """ Delete a recording by ID if the user owns it. """
    recording = db.query(VoiceRecording).filter_by(id=recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    if recording.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    db.delete(recording)
    db.commit()
    return {"message": "Recording deleted"}

@router.put("/recordings/{recording_id}")
def update_recording(recording_id: str, file_url: str, db: Session = Depends(get_session), current_user: dict = Depends(get_current_user)):
    """ Update recording details. """
    recording = db.query(VoiceRecording).filter_by(id=recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    if recording.user_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Unauthorized")
    
    recording.file_url = file_url
    db.commit()
    db.refresh(recording)
    return {"message": "Recording updated", "recording": recording}

@router.get("/recordings/user/{user_id}")
def get_recordings_by_user(user_id: str, db: Session = Depends(get_session)):
    """ Get all recordings for a user. """
    recordings = db.query(VoiceRecording).filter_by(user_id=user_id).all()
    return {"recordings": recordings}

@router.get("/recordings/store/{store_id}")
def get_recordings_by_store(store_id: str, db: Session = Depends(get_session)):
    """ Get all recordings for a store (assuming user_id represents stores). """
    recordings = db.query(VoiceRecording).filter_by(user_id=store_id).all()
    return {"recordings": recordings}
