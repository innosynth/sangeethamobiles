from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.Transcription.TranscriptionModel import Transcription
from backend.schemas.TranscriptionSchema import TransctriptionStatus 


def transcribe_audio(recording, recording_id, db):
    recording = (
        db.query(VoiceRecording).filter(VoiceRecording.id == recording_id).first()
    )
    if not recording:
        return False

    transcription_text = (
        f"Transcription for recording {recording_id}"
    )
    transcription = Transcription(
        audio_id=recording_id, transcription_text=transcription_text
    )
    db.add(transcription)
    recording.transcription_status = TransctriptionStatus.completed
    db.commit()
    return True
