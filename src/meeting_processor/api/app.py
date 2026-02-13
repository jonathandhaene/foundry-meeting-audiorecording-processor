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
    custom_terms: Optional[str] = Field(
        default=None,
        description="Comma-separated list of custom terms for improved recognition"
    )
    language_candidates: Optional[str] = Field(
        default=None,
        description="Comma-separated list of language codes for multi-language support (e.g., 'en-US,nl-NL')"
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
    enable_nlp: bool = Form(default=True),
    custom_terms: Optional[str] = Form(default=None),
    language_candidates: Optional[str] = Form(default=None),
    terms_file: Optional[UploadFile] = File(default=None, description="Optional file with custom terms (one per line)")
):
    """
    Upload an audio file and start transcription.
    
    Returns a job ID for tracking progress.
    """
    # Generate job ID
    job_id = str(uuid.uuid4())
    
    # Parse custom terms from text input or file
    terms_list = []
    if custom_terms:
        # Split by comma or newline and clean up
        terms_list = [term.strip() for term in custom_terms.replace('\n', ',').split(',') if term.strip()]
    
    # If terms file is uploaded, read and parse it
    if terms_file:
        try:
            terms_content = await terms_file.read()
            terms_text = terms_content.decode('utf-8')
            file_terms = [term.strip() for term in terms_text.split('\n') if term.strip()]
            terms_list.extend(file_terms)
        except Exception as e:
            logger.warning(f"Failed to read terms file: {e}")
    
    # Parse language candidates
    lang_candidates_list = []
    if language_candidates:
        lang_candidates_list = [lang.strip() for lang in language_candidates.split(',') if lang.strip()]
    
    # Save uploaded audio file
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
        "custom_terms": terms_list,
        "language_candidates": lang_candidates_list,
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
        enable_nlp=enable_nlp,
        custom_terms=terms_list,
        language_candidates=lang_candidates_list
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
    enable_nlp: bool,
    custom_terms: Optional[List[str]] = None,
    language_candidates: Optional[List[str]] = None
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
                enable_diarization=enable_diarization,
                custom_terms=custom_terms,
                language_candidates=language_candidates
            )
            transcription_result = transcriber.transcribe_audio(processed_path)
        
        elif method == "whisper_local":
            transcriber = WhisperTranscriber(
                model_size=whisper_model,
                language=language,
                use_api=False,
                custom_terms=custom_terms
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
                api_key=openai_key,
                custom_terms=custom_terms
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


@app.get("/api/audio/{job_id}")
async def serve_audio(job_id: str):
    """
    Serve the audio file for a completed job.
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_db[job_id]
    file_path = Path(job["file_path"])
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    from fastapi.responses import FileResponse
    return FileResponse(
        path=str(file_path),
        media_type="audio/wav",
        filename=job["filename"]
    )


@app.post("/api/export/{job_id}")
async def export_transcription(job_id: str, format: str = Form(...)):
    """
    Export transcription in different formats (txt, docx, pdf).
    """
    if job_id not in jobs_db:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = jobs_db[job_id]
    
    if job["status"] != JobStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    if not job.get("result"):
        raise HTTPException(status_code=404, detail="No transcription result found")
    
    transcription = job["result"]["transcription"]
    nlp_analysis = job["result"].get("nlp_analysis")
    
    try:
        if format == "txt":
            return export_as_txt(transcription, nlp_analysis, job["filename"])
        elif format == "docx":
            return export_as_docx(transcription, nlp_analysis, job["filename"])
        elif format == "pdf":
            return export_as_pdf(transcription, nlp_analysis, job["filename"])
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported format: {format}")
    except Exception as e:
        logger.error(f"Export failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


def export_as_txt(transcription: Dict[str, Any], nlp_analysis: Optional[Dict[str, Any]], filename: str):
    """Export transcription as plain text file."""
    from fastapi.responses import Response
    from io import StringIO
    
    output = StringIO()
    output.write(f"Transcription: {filename}\n")
    output.write("=" * 80 + "\n\n")
    
    # Metadata
    if transcription.get("language"):
        output.write(f"Language: {transcription['language']}\n")
    if transcription.get("duration"):
        output.write(f"Duration: {transcription['duration']:.2f} seconds\n")
    if transcription.get("metadata", {}).get("speaker_count"):
        output.write(f"Speakers: {transcription['metadata']['speaker_count']}\n")
    output.write("\n")
    
    # Full text
    output.write("Full Transcription:\n")
    output.write("-" * 80 + "\n")
    output.write(transcription.get("full_text", "") + "\n\n")
    
    # Segments with timestamps
    if transcription.get("segments"):
        output.write("\nDetailed Segments:\n")
        output.write("-" * 80 + "\n")
        for segment in transcription["segments"]:
            timestamp = f"[{segment['start_time']:.1f}s - {segment['end_time']:.1f}s]"
            speaker = f"{segment.get('speaker_id', 'Unknown')}: " if segment.get('speaker_id') else ""
            output.write(f"{timestamp} {speaker}{segment['text']}\n")
    
    # NLP Analysis
    if nlp_analysis:
        output.write("\n\nContent Analysis:\n")
        output.write("=" * 80 + "\n")
        
        if nlp_analysis.get("sentiment"):
            output.write(f"\nSentiment: {nlp_analysis['sentiment'].get('overall', 'N/A')}\n")
        
        if nlp_analysis.get("key_phrases"):
            output.write("\nKey Phrases:\n")
            for phrase in nlp_analysis["key_phrases"][:20]:
                output.write(f"  - {phrase['text']}\n")
    
    content = output.getvalue()
    return Response(
        content=content,
        media_type="text/plain",
        headers={"Content-Disposition": f"attachment; filename={filename.rsplit('.', 1)[0]}.txt"}
    )


def export_as_docx(transcription: Dict[str, Any], nlp_analysis: Optional[Dict[str, Any]], filename: str):
    """Export transcription as Word document."""
    from docx import Document
    from docx.shared import Pt, RGBColor
    from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
    from io import BytesIO
    from fastapi.responses import Response
    
    doc = Document()
    
    # Title
    title = doc.add_heading(f"Transcription: {filename}", 0)
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    
    # Metadata section
    doc.add_heading("Metadata", level=1)
    metadata_para = doc.add_paragraph()
    if transcription.get("language"):
        metadata_para.add_run(f"Language: ").bold = True
        metadata_para.add_run(f"{transcription['language']}\n")
    if transcription.get("duration"):
        metadata_para.add_run(f"Duration: ").bold = True
        metadata_para.add_run(f"{transcription['duration']:.2f} seconds\n")
    if transcription.get("metadata", {}).get("speaker_count"):
        metadata_para.add_run(f"Speakers: ").bold = True
        metadata_para.add_run(f"{transcription['metadata']['speaker_count']}\n")
    
    # Full transcription
    doc.add_heading("Full Transcription", level=1)
    doc.add_paragraph(transcription.get("full_text", ""))
    
    # Segments
    if transcription.get("segments"):
        doc.add_page_break()
        doc.add_heading("Detailed Segments", level=1)
        for segment in transcription["segments"]:
            para = doc.add_paragraph()
            # Timestamp
            timestamp_run = para.add_run(f"[{segment['start_time']:.1f}s - {segment['end_time']:.1f}s] ")
            timestamp_run.font.color.rgb = RGBColor(0, 102, 204)
            timestamp_run.bold = True
            # Speaker
            if segment.get('speaker_id'):
                speaker_run = para.add_run(f"{segment['speaker_id']}: ")
                speaker_run.font.color.rgb = RGBColor(155, 89, 182)
                speaker_run.bold = True
            # Text
            para.add_run(segment['text'])
    
    # NLP Analysis
    if nlp_analysis:
        doc.add_page_break()
        doc.add_heading("Content Analysis", level=1)
        
        if nlp_analysis.get("sentiment"):
            doc.add_heading("Sentiment", level=2)
            doc.add_paragraph(f"Overall: {nlp_analysis['sentiment'].get('overall', 'N/A')}")
        
        if nlp_analysis.get("key_phrases"):
            doc.add_heading("Key Phrases", level=2)
            for phrase in nlp_analysis["key_phrases"][:20]:
                doc.add_paragraph(phrase['text'], style='List Bullet')
    
    # Save to BytesIO
    bio = BytesIO()
    doc.save(bio)
    bio.seek(0)
    
    return Response(
        content=bio.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f"attachment; filename={filename.rsplit('.', 1)[0]}.docx"}
    )


def export_as_pdf(transcription: Dict[str, Any], nlp_analysis: Optional[Dict[str, Any]], filename: str):
    """Export transcription as PDF document."""
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from io import BytesIO
    from fastapi.responses import Response
    
    bio = BytesIO()
    doc = SimpleDocTemplate(bio, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    story = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor='#667eea',
        alignment=TA_CENTER,
        spaceAfter=12
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor='#667eea',
        spaceAfter=8
    )
    
    # Title
    story.append(Paragraph(f"Transcription: {filename}", title_style))
    story.append(Spacer(1, 0.2*inch))
    
    # Metadata
    story.append(Paragraph("Metadata", heading_style))
    metadata_text = ""
    if transcription.get("language"):
        metadata_text += f"<b>Language:</b> {transcription['language']}<br/>"
    if transcription.get("duration"):
        metadata_text += f"<b>Duration:</b> {transcription['duration']:.2f} seconds<br/>"
    if transcription.get("metadata", {}).get("speaker_count"):
        metadata_text += f"<b>Speakers:</b> {transcription['metadata']['speaker_count']}<br/>"
    story.append(Paragraph(metadata_text, styles['Normal']))
    story.append(Spacer(1, 0.2*inch))
    
    # Full transcription
    story.append(Paragraph("Full Transcription", heading_style))
    story.append(Paragraph(transcription.get("full_text", ""), styles['Normal']))
    story.append(PageBreak())
    
    # Segments
    if transcription.get("segments"):
        story.append(Paragraph("Detailed Segments", heading_style))
        for segment in transcription["segments"]:
            timestamp = f"[{segment['start_time']:.1f}s - {segment['end_time']:.1f}s]"
            speaker = f"<b>{segment.get('speaker_id', 'Unknown')}:</b> " if segment.get('speaker_id') else ""
            text = f'<font color="#3498db">{timestamp}</font> {speaker}{segment["text"]}'
            story.append(Paragraph(text, styles['Normal']))
            story.append(Spacer(1, 0.05*inch))
    
    # NLP Analysis
    if nlp_analysis:
        story.append(PageBreak())
        story.append(Paragraph("Content Analysis", heading_style))
        
        if nlp_analysis.get("sentiment"):
            story.append(Paragraph("Sentiment", styles['Heading3']))
            story.append(Paragraph(f"Overall: {nlp_analysis['sentiment'].get('overall', 'N/A')}", styles['Normal']))
            story.append(Spacer(1, 0.1*inch))
        
        if nlp_analysis.get("key_phrases"):
            story.append(Paragraph("Key Phrases", styles['Heading3']))
            phrases = ", ".join([phrase['text'] for phrase in nlp_analysis["key_phrases"][:20]])
            story.append(Paragraph(phrases, styles['Normal']))
    
    # Build PDF
    doc.build(story)
    bio.seek(0)
    
    return Response(
        content=bio.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename.rsplit('.', 1)[0]}.pdf"}
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
