from backend.AudioProcessing.VoiceRecordingModel import VoiceRecording
from backend.Transcription.TranscriptionModel import Transcription, TranscribeAI
from backend.schemas.TranscriptionSchema import TransctriptionStatus 
import os
import google.generativeai as genai
from dotenv import load_dotenv
import uuid,requests,json

load_dotenv()
GeminiKey= os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GeminiKey)
REQUEST_TIMEOUT = 1800.0
MODEL_NAME = "gemini-2.0-flash"

# Prompt for the model
PROMPT = PROMPT = """
As a audio analyzer and data manager,you should translate the provided call audio from its native language accurately into English language with speaker diarization. Ensure that every spoken segment is translated fully and verbatim. Clearly label each speaker (e.g., "Staff", "Customer") in the translation output.
Staff: — for the company representative
Customer: — for the customer
In addition to translation, perform a detailed analysis for each speaker and the conversation content. For every Customer segment, extract the following details:
 
Instructions for Analysis:
1)Perform a detailed analysis considering only the Customer side (excluding Staff) for analysis purposes.
 
For the Translation section:
1)Provide the complete English translation of the conversation(avoits ).
2)Maintain the original meaning and context.
3)Use clear speaker labels: Staff and Customer
 
For the Analysis section:
1)Consider only the Customer's speech content for the following analysis details:
 
Output the results in this exact JSON format:
{
  "Translation": [
    {
      "speaker": "Staff",
      "text": "Translated English text here"
    },
    {
      "speaker": "Customer",
      "text": "Translated English text here"
    },
    ...
  ],
  "analysis": {
    "customer_details": {
      "gender": "male/female/unknown",
      "language": "Primary language spoken originally",
      "emotional_state": ["emotion1", "emotion2"]
    },
    "content": {
      "product_mentions": ["product1", "product2"],
      "complaints": ["complaint1", "complaint2"],
      "positive_keywords": ["positive word1", "positive word2"],
      "negative_keywords": ["negative word1", "negative word2"],
      "contact_reason": ["Primary reason category 1", "Primary reason category 2"],
      "customer_interest": ["interest1", "interest2"]
    }
  }
}"""


def upload_audio_file(file_path: str, display_name: str):
    """Uploads an audio file to Google Generative AI."""
    try:
        return genai.upload_file(
            path=file_path,
            display_name=display_name,
        )
    except Exception as e:
        print("Error in Uploading",e)
        print(e)
        return False
    
def generate_audio_translation(model, prompt: str, uploaded_file, timeout: float):
    """Generates translation and transcription from the uploaded audio file."""
    print("Sending prompt to the model...")
    try:
        response = model.generate_content(
            contents=[prompt, uploaded_file],
            request_options={"timeout": timeout},
            generation_config={'response_mime_type': 'application/json'}
        )
        # print("Transcription:",response.text)
        return response
    except Exception as e:
        print("Error in Transcription",e)
        print(e)
        return False
def get_ai_transcription(file_path,recording_id):
    try:
        uploaded_file = upload_audio_file(file_path, recording_id)
        model = genai.GenerativeModel(model_name=MODEL_NAME)
        if(uploaded_file==False):
            return False
        # Generate response
        response = generate_audio_translation(model, PROMPT, uploaded_file, REQUEST_TIMEOUT)
        if(response==False):
            return False
        
        return json.loads(response.text)
    except Exception as e:
        print("Error in AI",e)
        print(e)
        return False

def transcribe_audio( recording_id, db):
    recording = (
        db.query(VoiceRecording).filter(VoiceRecording.id == recording_id).first()
    )
    # print(recording.file_url)
    if not recording:
        return False
    try:
        unique_filename = f"./upload_files/{uuid.uuid4()}.mp3"
        response = requests.get(recording.file_url, stream=True)
        if response.status_code == 200:
            with open(unique_filename, "wb") as file:
                for chunk in response.iter_content(chunk_size=1024):
                    file.write(chunk)
        response=get_ai_transcription(unique_filename,recording_id)
        
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
        print("Error in Storing",e)
        recording.transcription_status = TransctriptionStatus.failure
        db.commit()
    finally:
        db.close()
        os.remove(unique_filename)
