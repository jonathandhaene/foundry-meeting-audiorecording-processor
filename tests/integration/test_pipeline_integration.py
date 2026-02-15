"""Integration tests for the complete pipeline."""

import pytest
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from meeting_processor.pipeline import MeetingProcessor
from meeting_processor.utils import ConfigManager


@pytest.fixture
def mock_env():
    """Mock environment variables for testing."""
    env_vars = {
        "AZURE_SPEECH_KEY": "test_speech_key",
        "AZURE_SPEECH_REGION": "eastus",
        "AZURE_TEXT_ANALYTICS_KEY": "test_analytics_key",
        "AZURE_TEXT_ANALYTICS_ENDPOINT": "https://test.endpoint.com",
    }

    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(b"RIFF")
        f.write((36).to_bytes(4, "little"))
        f.write(b"WAVE")
        temp_path = f.name

    yield temp_path

    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestPipelineIntegration:
    """Integration tests for the meeting processor pipeline."""

    @patch("meeting_processor.pipeline.AzureSpeechTranscriber")
    @patch("meeting_processor.pipeline.ContentAnalyzer")
    @patch("meeting_processor.pipeline.AudioPreprocessor")
    def test_processor_initialization(self, mock_preprocessor, mock_analyzer, mock_transcriber, mock_env):
        """Test initializing the meeting processor."""
        processor = MeetingProcessor()

        assert processor is not None
        assert processor.audio_preprocessor is not None
        assert processor.transcriber is not None
        assert processor.content_analyzer is not None

    def test_processor_initialization_without_config(self):
        """Test initialization fails without proper config."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError):
                MeetingProcessor()

    @patch("meeting_processor.pipeline.AzureSpeechTranscriber")
    @patch("meeting_processor.pipeline.ContentAnalyzer")
    @patch("meeting_processor.audio.preprocessor.AudioPreprocessor.normalize_audio")
    def test_preprocess_audio(self, mock_normalize, mock_analyzer, mock_transcriber, mock_env, temp_audio_file):
        """Test audio preprocessing step."""
        mock_normalize.return_value = "/path/to/normalized.wav"

        processor = MeetingProcessor()

        with patch.object(processor.audio_preprocessor, "get_audio_info", return_value={}):
            result = processor.preprocess_audio(temp_audio_file)

        assert result == "/path/to/normalized.wav"
        mock_normalize.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
