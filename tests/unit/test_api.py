"""
Unit tests for the FastAPI application.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient
import tempfile
from pathlib import Path

from meeting_processor.api.app import app, jobs_db


@pytest.fixture
def client():
    """Create test client."""
    # Clear jobs database before each test
    jobs_db.clear()
    return TestClient(app)


@pytest.fixture
def mock_audio_file():
    """Create a mock audio file."""
    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    temp_file.write(b"fake audio data")
    temp_file.close()
    yield temp_file.name
    Path(temp_file.name).unlink(missing_ok=True)


class TestRootEndpoints:
    """Test root and health endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns service info."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Meeting Audio Transcription API"
        assert data["version"] == "1.0.0"
        assert data["status"] == "active"

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data


class TestTranscriptionEndpoint:
    """Test transcription upload and job creation."""

    @patch("meeting_processor.api.app.process_transcription")
    def test_upload_audio_file_azure(self, mock_process, client, mock_audio_file):
        """Test uploading audio file with Azure method."""
        with open(mock_audio_file, "rb") as f:
            response = client.post(
                "/api/transcribe",
                files={"file": ("test.wav", f, "audio/wav")},
                data={"method": "azure", "language": "en-US", "enable_diarization": "true", "enable_nlp": "true"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert data["message"] == "Transcription job started"

        # Verify job was created in database
        assert data["job_id"] in jobs_db
        job = jobs_db[data["job_id"]]
        assert job["method"] == "azure"
        assert job["language"] == "en-US"
        assert job["enable_diarization"] is True

    @patch("meeting_processor.api.app.process_transcription")
    def test_upload_audio_file_whisper(self, mock_process, client, mock_audio_file):
        """Test uploading audio file with Whisper method."""
        with open(mock_audio_file, "rb") as f:
            response = client.post(
                "/api/transcribe",
                files={"file": ("test.wav", f, "audio/wav")},
                data={"method": "whisper_local", "whisper_model": "base", "enable_nlp": "false"},
            )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data

        # Verify job configuration
        job = jobs_db[data["job_id"]]
        assert job["method"] == "whisper_local"
        assert job["whisper_model"] == "base"
        assert job["enable_nlp"] is False

    def test_upload_without_file(self, client):
        """Test that uploading without a file returns error."""
        response = client.post("/api/transcribe", data={"method": "azure"})
        assert response.status_code == 422  # Validation error


class TestJobStatusEndpoint:
    """Test job status retrieval."""

    def test_get_job_status_success(self, client):
        """Test getting status of existing job."""
        # Create a mock job
        job_id = "test-job-123"
        jobs_db[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "filename": "test.wav",
            "method": "azure",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:01:00",
            "result": {"transcription": {"full_text": "Test transcription"}},
            "error": None,
        }

        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "completed"
        assert data["result"]["transcription"]["full_text"] == "Test transcription"

    def test_get_job_status_not_found(self, client):
        """Test getting status of non-existent job."""
        response = client.get("/api/jobs/non-existent-job")
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"


class TestListJobsEndpoint:
    """Test listing all jobs."""

    def test_list_jobs_empty(self, client):
        """Test listing jobs when none exist."""
        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert data["jobs"] == []

    def test_list_jobs_with_data(self, client):
        """Test listing jobs with existing data."""
        # Create mock jobs
        jobs_db["job1"] = {
            "job_id": "job1",
            "status": "completed",
            "filename": "file1.wav",
            "method": "azure",
            "created_at": "2024-01-01T00:00:00",
        }
        jobs_db["job2"] = {
            "job_id": "job2",
            "status": "processing",
            "filename": "file2.wav",
            "method": "whisper_local",
            "created_at": "2024-01-01T00:01:00",
        }

        response = client.get("/api/jobs")
        assert response.status_code == 200
        data = response.json()
        assert len(data["jobs"]) == 2
        assert any(job["job_id"] == "job1" for job in data["jobs"])
        assert any(job["job_id"] == "job2" for job in data["jobs"])


class TestDeleteJobEndpoint:
    """Test job deletion."""

    def test_delete_job_success(self, client):
        """Test successful job deletion."""
        # Create a mock job
        job_id = "test-job-delete"
        temp_file = tempfile.NamedTemporaryFile(delete=False)
        temp_file.close()

        jobs_db[job_id] = {
            "job_id": job_id,
            "status": "completed",
            "file_path": temp_file.name,
            "filename": "test.wav",
            "method": "azure",
            "created_at": "2024-01-01T00:00:00",
        }

        response = client.delete(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "Job deleted successfully"
        assert job_id not in jobs_db

    def test_delete_job_not_found(self, client):
        """Test deleting non-existent job."""
        response = client.delete("/api/jobs/non-existent-job")
        assert response.status_code == 404
        assert response.json()["detail"] == "Job not found"


class TestProcessTranscription:
    """Test background transcription processing."""

    @patch("meeting_processor.api.app.ConfigManager")
    @patch("meeting_processor.api.app.AudioPreprocessor")
    @patch("meeting_processor.api.app.AzureSpeechTranscriber")
    def test_process_transcription_azure_success(self, mock_transcriber_class, mock_preprocessor_class, mock_config_class):
        """Test successful Azure transcription processing."""
        from meeting_processor.api.app import process_transcription
        from meeting_processor.transcription.transcriber import TranscriptionResult, TranscriptionSegment

        # Setup mocks
        mock_config = Mock()
        mock_config.azure_speech_key = "test_key"
        mock_config.azure_speech_region = "test_region"
        mock_config.default_language = "en-US"
        mock_config_class.return_value = mock_config

        mock_preprocessor = Mock()
        mock_preprocessor.preprocess_audio.return_value = "/tmp/processed.wav"
        mock_preprocessor_class.return_value = mock_preprocessor

        mock_transcriber = Mock()
        mock_result = TranscriptionResult(
            segments=[
                TranscriptionSegment(text="Hello world", start_time=0.0, end_time=2.0, speaker_id="Speaker-1", confidence=0.95)
            ],
            full_text="Hello world",
            duration=2.0,
            language="en-US",
            metadata={"diarization_enabled": True},
        )
        mock_transcriber.transcribe_audio.return_value = mock_result
        mock_transcriber_class.return_value = mock_transcriber

        # Create job
        job_id = "test-job-process"
        jobs_db[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.wav",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Process transcription
        process_transcription(
            job_id=job_id,
            file_path="/tmp/test.wav",
            method="azure",
            language="en-US",
            enable_diarization=True,
            chunk_size=None,
            whisper_model="base",
            enable_nlp=False,
        )

        # Verify job completed successfully
        assert jobs_db[job_id]["status"] == "completed"
        assert jobs_db[job_id]["result"] is not None
        assert "transcription" in jobs_db[job_id]["result"]
        assert jobs_db[job_id]["error"] is None

    @patch("meeting_processor.api.app.ConfigManager")
    @patch("meeting_processor.api.app.AudioPreprocessor")
    def test_process_transcription_failure(self, mock_preprocessor_class, mock_config_class):
        """Test transcription processing with error."""
        from meeting_processor.api.app import process_transcription

        # Setup mocks to raise exception
        mock_config_class.return_value = Mock()
        mock_preprocessor = Mock()
        mock_preprocessor.preprocess_audio.side_effect = Exception("Processing error")
        mock_preprocessor_class.return_value = mock_preprocessor

        # Create job
        job_id = "test-job-fail"
        jobs_db[job_id] = {
            "job_id": job_id,
            "status": "pending",
            "file_path": "/tmp/test.wav",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
        }

        # Process transcription
        process_transcription(
            job_id=job_id,
            file_path="/tmp/test.wav",
            method="azure",
            language=None,
            enable_diarization=True,
            chunk_size=None,
            whisper_model="base",
            enable_nlp=False,
        )

        # Verify job failed
        assert jobs_db[job_id]["status"] == "failed"
        assert jobs_db[job_id]["error"] is not None
        assert "Processing error" in jobs_db[job_id]["error"]
