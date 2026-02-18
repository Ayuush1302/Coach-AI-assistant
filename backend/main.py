from fastapi import FastAPI, UploadFile, File, HTTPException
from pydantic import BaseModel
import uvicorn
import shutil
import os
import ssl
import certifi

# Fix for SSL certificate verify failed on Mac
os.environ['SSL_CERT_FILE'] = certifi.where()
ssl._create_default_https_context = ssl._create_unverified_context

import whisper
# import spacy
from parser import parse_workout_text

app = FastAPI()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all origins for dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Whisper model (using "base" for balance of speed/accuracy)
print("Loading Whisper model...")
model = whisper.load_model("base")
print("Whisper model loaded.")

# Placeholder for SpaCy model
# nlp = spacy.load("en_core_web_sm")

class ParseRequest(BaseModel):
    text: str

@app.get("/")
def read_root():
    return {"message": "AI Workout Assignment API"}

@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    audio_path = f"temp_{file.filename}"
    
    try:
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Transcribe
        result = model.transcribe(audio_path)
        return {"text": result["text"].strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Cleanup
        if os.path.exists(audio_path):
            os.remove(audio_path)

import csv
from datetime import datetime

# ... imports ...

@app.post("/parse")
def parse_workout(request: ParseRequest):
    structured_data = parse_workout_text(request.text)
    
    # Log valid transcriptions for dataset collection (Phase 2 preparation)
    if structured_data.get("original_text") and not structured_data.get("error"):
        log_file = "training_data.csv"
        file_exists = os.path.isfile(log_file)
        
        with open(log_file, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(["timestamp", "transcription", "parsed_json"])
            
            writer.writerow([
                datetime.now().isoformat(), 
                structured_data["original_text"], 
                str(structured_data)
            ])
            
    return structured_data

@app.post("/assign")
def assign_workout(data: dict):
    # Mock database save
    return {"status": "success", "data": data}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
