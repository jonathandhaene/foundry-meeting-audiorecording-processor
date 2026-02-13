"""
FastAPI application for the Meeting Audio Transcription service.

Provides REST API endpoints for uploading audio files and running
transcription with different methods (Azure Speech, Whisper).
"""

import os
import logging
import uuid
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum

from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..transcription.transcriber import AzureSpeechTranscriber
from ..transcription.whisper_transcriber import WhisperTranscriber
from ..audio.preprocessor import AudioPreprocessor
from ..nlp.analyzer import ContentAnalyzer
from ..utils.config import ConfigManager

logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Meeting Audio Transcription API",
    description="Upload audio files and transcribe using Azure Speech Services or Whisper",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Job storage (use Redis or database in production)
jobs_db: Dict[str, Dict[str, Any]] = {}

# Temporary file storage directory
TEMP_DIR = Path(tempfile.gettempdir()) / "meeting_transcription"
TEMP_DIR.mkdir(exist_ok=True)


class TranscriptionMethod(str, Enum):
    """Available transcription methods."""
    AZURE = "azure"
    WHISPER_LOCAL = "whisper_local"
    WHISPER_API = "whisper_api"


class JobStatus(str, Enum):
    """Job status enumeration."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TranscriptionRequest(BaseModel):
    """Request model for transcription."""
    method: TranscriptionMethod = Field(
        default=TranscriptionMethod.AZURE,
        description="Transcription method to use"
    )
    language: Optional[str] = Field(
        default=None,
        description="Language code (e.g., 'en-US', 'es-ES') or None for auto-detect"
    )
    enable_diarization: bool = Field(
        default=True,
        description="Enable speaker diarization (Azure only)"
    )
    chunk_size: Optional[int] = Field(
        default=None,
        description="Audio chunk size in seconds for large files"
    )
    whisper_model: str = Field(
        default="base",
        description="Whisper model size (tiny, base, small, medium, large)"
    )
    enable_nlp: bool = Field(
        default=True,
        description="Enable NLP analysis (key phrases, sentiment, etc.)"
    )


class JobResponse(BaseModel):
    """Response model for job submission."""
    job_id: str
    status: JobStatus
    message: str


class JobStatusResponse(BaseModel):
    """Response model for job status."""
    job_id: str
    status: JobStatus
    progress: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str
    updated_at: str


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Meeting Audio Transcription API",
        "version": "1.0.0",
        "status": "active"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.post("/api/transcribe", response_model=JobResponse)
async def transcribe_audio(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(..., description="Audio file to transcribe"),
    method: str = Form(default="azure"),
    language: Optional[str] = Form(default=None),
    enable_diarization: bool = Form(default=True),
    chunk_size: Optional[int] = Form(default=None),
    whisper_model: str = Form(default="base"),
    enable_nlp: bool = Form(default=True)
):
    """
    Upload an audio file and start transcription.
    
    Returns a job ID for tracking progress.
    """
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Save uploaded file
    file_path = TEMP_DIR / f"{job_id}_{file.filename}"
    try:
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
    except Exception as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")
    
    # Create job record
    jobs_db[job_id] = {
        "job_id": job_id,
        "status": JobStatus.PENDING,
        "file_path": str(file_path),
        "filename": file.filename,
        "method": method,
        "language": language,
        "enable_diarization": enable_diarization,
        "chunk_size": chunk_size,
        "whisper_model": whisper_model,
        "enable_nlp": enable_nlp,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "result": None,
        "error": None
    }
    
    # Schedule background task
    background_tasks.add_task(
        process_transcription,
        job_id=job_id,
        file_path=str(file_path),
        method=method,
        language=language,
        enable_diarization=enable_diarization,
        chunk_size=chunk_size,
        whisper_model=whisper_model,
        enable_nlp=enable_nlp
    )
    
    return JobResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message="Transcription job started"
    )


@app.get("/api/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str):
    """
    Get the status of a transcription job.
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_db[job_id]
    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job.get("progress"),
        result=job.get("result"),
        error=job.get("error"),
        created_at=job["created_at"],
        updated_at=job["updated_at"]
    )


@app.get("/api/jobs")
async def list_jobs():
    """
    List all transcription jobs.
    """
    return {
        "jobs": [
            {
                "job_id": job["job_id"],
                "status": job["status"],
                "filename": job["filename"],
                "method": job["method"],
                "created_at": job["created_at"]
            }
            for job in jobs_db.values()
        ]
    }


@app.delete("/api/jobs/{job_id}")
async def delete_job(job_id: str):
    """
    Delete a transcription job and its associated files.
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_db[job_id]
    
    # Clean up files
    try:
        file_path = Path(job["file_path"])
        if file_path.exists():
            file_path.unlink()
    except Exception as e:
        logger.warning(f"Failed to delete file: {e}")
    
    # Remove from database
    del jobs_db[job_id]
    
    return {"message": "Job deleted successfully"}


def process_transcription(
    job_id: str,
    file_path: str,
    method: str,
    language: Optional[str],
    enable_diarization: bool,
    chunk_size: Optional[int],
    whisper_model: str,
    enable_nlp: bool
):
    """
    Background task to process transcription.
    """
    try:
        # Update status
        jobs_db[job_id]["status"] = JobStatus.PROCESSING
        jobs_db[job_id]["updated_at"] = datetime.utcnow().isoformat()
        jobs_db[job_id]["progress"] = "Starting transcription..."
        
        # Load configuration
        config = ConfigManager()
        
        # Preprocess audio
        jobs_db[job_id]["progress"] = "Preprocessing audio..."
        preprocessor = AudioPreprocessor()
        processed_path = preprocessor.preprocess_audio(file_path)
        
        # Transcribe based on method
        jobs_db[job_id]["progress"] = "Transcribing audio..."
        
        if method == "azure":
            transcriber = AzureSpeechTranscriber(
                speech_key=config.azure_speech_key,
                speech_region=config.azure_speech_region,
                language=language or config.default_language,
                enable_diarization=enable_diarization
            )
            transcription_result = transcriber.transcribe_audio(processed_path)
        
        elif method == "whisper_local":
            transcriber = WhisperTranscriber(
                model_size=whisper_model,
                language=language,
                use_api=False
            )
            transcription_result = transcriber.transcribe_audio(
                processed_path,
                enable_diarization=enable_diarization
            )
        
        elif method == "whisper_api":
            openai_key = os.getenv("OPENAI_API_KEY")
            if not openai_key:
                raise ValueError("OPENAI_API_KEY not configured")
            
            transcriber = WhisperTranscriber(
                language=language,
                use_api=True,
                api_key=openai_key
            )
            transcription_result = transcriber.transcribe_audio(processed_path)
        
        else:
            raise ValueError(f"Unknown transcription method: {method}")
        
        result = {
            "transcription": transcription_result.to_dict()
        }
        
        # Perform NLP analysis if enabled
        if enable_nlp and transcription_result.full_text:
            jobs_db[job_id]["progress"] = "Analyzing content..."
            analyzer = ContentAnalyzer(
                text_analytics_key=config.azure_text_analytics_key,
                text_analytics_endpoint=config.azure_text_analytics_endpoint
            )
            nlp_result = analyzer.analyze_text(transcription_result.full_text)
            result["nlp_analysis"] = nlp_result
        
        # Update job with results
        jobs_db[job_id]["status"] = JobStatus.COMPLETED
        jobs_db[job_id]["result"] = result
        jobs_db[job_id]["progress"] = "Completed"
        jobs_db[job_id]["updated_at"] = datetime.utcnow().isoformat()
        
        logger.info(f"Job {job_id} completed successfully")
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {e}", exc_info=True)
        jobs_db[job_id]["status"] = JobStatus.FAILED
        jobs_db[job_id]["error"] = str(e)
        jobs_db[job_id]["updated_at"] = datetime.utcnow().isoformat()
    
    finally:
        # Clean up processed file
        try:
            if processed_path and os.path.exists(processed_path):
                os.unlink(processed_path)
        except Exception as e:
            logger.warning(f"Failed to clean up processed file: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
