from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.Transcription.TranscriptionModel import Transcription
from backend.schemas.TranscriptionSchema import TransctriptionStatus 
import os
import google.generativeai as genai
from dotenv import load_dotenv
import uuid,requests

load_dotenv()
GeminiKey= os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GeminiKey)
# Constants
REQUEST_TIMEOUT = 1800.0
MODEL_NAME = "gemini-2.0-flash"

# Prompt for the model
PROMPT = """
Translate the given audio into English.

First, transcribe the speech in the original/native language.

Then, provide the English translation.

Maintain speaker diarization: clearly separate and label each speaker (e.g., Speaker 1, Speaker 2).

Note: Ensure accurate transcription and translation with 99.99% accuracy.
Output format:
Speaker 1 (Native Language): [Transcription]
Speaker 1 (English Translation): [Translation]
Speaker 2 (Native Language): [Transcription]
Speaker 2 (English Translation): [Translation]
...
"""

def upload_audio_file(file_path: str, display_name: str):
    """Uploads an audio file to Google Generative AI."""
    try:
        return genai.upload_file(
            path=file_path,
            display_name=display_name,
        )
    except Exception as e:
        print(e)
        return False
    
def generate_audio_translation(model, prompt: str, uploaded_file, timeout: float):
    """Generates translation and transcription from the uploaded audio file."""
    print("Sending prompt to the model...")
    try:
        response = model.generate_content(
            contents=[prompt, uploaded_file],
            request_options={"timeout": timeout}
        )
        print("Transcription:",response.text)
        return response
    except Exception as e:
        print(e)
        return False


def transcribe_audio( recording_id, db):
    recording = (
        db.query(VoiceRecording).filter(VoiceRecording.id == recording_id).first()
    )
    print(recording.file_url)
    if not recording:
        return False
    try:
        unique_filename = f"./temp/{uuid.uuid4()}.mp3"
        response = requests.get(recording.file_url, stream=True)
        if response.status_code == 200:
            with open(unique_filename, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    file.write(chunk)
        uploaded_file = upload_audio_file(unique_filename, recording_id)
        model = genai.GenerativeModel(model_name=MODEL_NAME)
        if(uploaded_file==False):
            recording.transcription_status = TransctriptionStatus.failure
            db.commit()
            return False
        # Generate response
        response = generate_audio_translation(model, PROMPT, uploaded_file, REQUEST_TIMEOUT)
        if(response==False):
            recording.transcription_status = TransctriptionStatus.failure
            db.commit()
            return False
        transcription_text = response.text
        transcription = Transcription(
            audio_id=recording_id, transcription_text=transcription_text
        )
        db.add(transcription)
        recording.transcription_status = TransctriptionStatus.completed
        db.commit()
        print("Process Completed")
        return True
    except Exception as e:
        print(e)
        recording.transcription_status = TransctriptionStatus.failure
        db.commit()
    finally:
        db.close()
        os.remove(unique_filename)
