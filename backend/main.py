from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import httpx
import shutil
import os
import csv
from datetime import datetime

# SSL fix for environments with certificate issues
try:
    import certifi
    os.environ['SSL_CERT_FILE'] = certifi.where()
except ImportError:
    pass

from parser import parse_workout_text

# ── Config ─────────────────────────────────────────────────────────────────────

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_WHISPER_MODEL = "whisper-large-v3-turbo"
GROQ_API_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# ── App Setup ──────────────────────────────────────────────────────────────────

app = FastAPI(title="Coach AI Assistant API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Models ─────────────────────────────────────────────────────────────────────

class ParseRequest(BaseModel):
    text: str

class AssignRequest(BaseModel):
    data: dict

# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/")
def read_root():
    return {"message": "AI Workout Assignment API"}


@app.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    """Transcribe audio using Groq Whisper API (whisper-large-v3-turbo)."""
    audio_path = f"temp_{file.filename}"

    try:
        # Save uploaded file temporarily
        with open(audio_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Send to Groq Whisper API
        async with httpx.AsyncClient(timeout=60.0) as client:
            with open(audio_path, "rb") as audio_file:
                response = await client.post(
                    GROQ_API_URL,
                    headers={
                        "Authorization": f"Bearer {GROQ_API_KEY}",
                    },
                    files={
                        "file": (file.filename, audio_file, file.content_type or "audio/wav"),
                    },
                    data={
                        "model": GROQ_WHISPER_MODEL,
                        "language": "en",
                    },
                )

        if response.status_code != 200:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Groq API error: {response.text}"
            )

        result = response.json()
        return {"text": result.get("text", "").strip()}

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Transcription timed out")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)


@app.post("/parse")
def parse_workout(request: ParseRequest):
    structured_data = parse_workout_text(request.text)

    # Log valid transcriptions for dataset collection
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
def assign_workout(request: AssignRequest):
    return {"status": "success", "data": request.data}


# ── Entry Point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
