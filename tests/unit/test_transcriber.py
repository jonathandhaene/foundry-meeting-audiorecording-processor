"""Unit tests for transcription module."""

import pytest
from unittest.mock import Mock, patch, MagicMock

from meeting_processor.transcription import (
    AzureSpeechTranscriber,
    TranscriptionSegment,
    TranscriptionResult
)


@pytest.fixture
def mock_speech_sdk():
    """Mock Azure Speech SDK."""
    with patch('meeting_processor.transcription.transcriber.speechsdk') as mock_sdk:
        # Mock SpeechConfig
        mock_config = Mock()
        mock_sdk.SpeechConfig.return_value = mock_config
        
        # Mock OutputFormat
        mock_sdk.OutputFormat.Detailed = "Detailed"
        
        # Mock ResultReason
        mock_sdk.ResultReason.RecognizedSpeech = "RecognizedSpeech"
        
        # Mock audio config
        mock_audio_config = Mock()
        mock_sdk.audio.AudioConfig.return_value = mock_audio_config
        
        yield mock_sdk


@pytest.fixture
def transcriber(mock_speech_sdk):
    """Create a transcriber instance with mocked SDK."""
    return AzureSpeechTranscriber(
        speech_key="test_key",
        speech_region="test_region",
        language="en-US"
    )


class TestTranscriptionSegment:
    """Test TranscriptionSegment dataclass."""

    def test_create_segment(self):
        """Test creating a transcription segment."""
        segment = TranscriptionSegment(
            text="Hello world",
            start_time=0.0,
            end_time=1.5,
            speaker_id="speaker1",
            confidence=0.95
        )
        
        assert segment.text == "Hello world"
        assert segment.start_time == 0.0
        assert segment.end_time == 1.5
        assert segment.speaker_id == "speaker1"
        assert segment.confidence == 0.95

    def test_segment_to_dict(self):
        """Test converting segment to dictionary."""
        segment = TranscriptionSegment(
            text="Test",
            start_time=0.0,
            end_time=1.0
        )
        
        result = segment.to_dict()
        
        assert isinstance(result, dict)
        assert result["text"] == "Test"
        assert result["start_time"] == 0.0
        assert result["end_time"] == 1.0


class TestTranscriptionResult:
    """Test TranscriptionResult dataclass."""

    def test_create_result(self):
        """Test creating a transcription result."""
        segments = [
            TranscriptionSegment("Hello", 0.0, 1.0),
            TranscriptionSegment("World", 1.0, 2.0)
        ]
        
        result = TranscriptionResult(
            segments=segments,
            full_text="Hello World",
            duration=2.0,
            language="en-US",
            metadata={"test": "value"}
        )
        
        assert len(result.segments) == 2
        assert result.full_text == "Hello World"
        assert result.duration == 2.0

    def test_result_to_dict(self):
        """Test converting result to dictionary."""
        segments = [TranscriptionSegment("Test", 0.0, 1.0)]
        result = TranscriptionResult(
            segments=segments,
            full_text="Test",
            duration=1.0,
            language="en-US",
            metadata={}
        )
        
        result_dict = result.to_dict()
        
        assert isinstance(result_dict, dict)
        assert "segments" in result_dict
        assert "full_text" in result_dict
        assert result_dict["full_text"] == "Test"


class TestAzureSpeechTranscriber:
    """Test AzureSpeechTranscriber class."""

    def test_initialization(self, mock_speech_sdk):
        """Test transcriber initialization."""
        transcriber = AzureSpeechTranscriber(
            speech_key="test_key",
            speech_region="test_region",
            language="en-US",
            enable_diarization=True,
            max_speakers=5
        )
        
        assert transcriber.speech_key == "test_key"
        assert transcriber.speech_region == "test_region"
        assert transcriber.language == "en-US"
        assert transcriber.enable_diarization is True
        assert transcriber.max_speakers == 5

    def test_initialization_without_sdk(self):
        """Test initialization fails without SDK."""
        with patch('meeting_processor.transcription.transcriber.speechsdk', None):
            with pytest.raises(ImportError):
                AzureSpeechTranscriber("key", "region")

    def test_extract_confidence(self, transcriber):
        """Test extracting confidence from result."""
        mock_result = Mock()
        mock_result.json = '{"NBest": [{"Confidence": 0.95}]}'
        
        confidence = transcriber._extract_confidence(mock_result)
        
        assert confidence == 0.95

    def test_extract_confidence_no_nbest(self, transcriber):
        """Test extracting confidence when NBest is missing."""
        mock_result = Mock()
        mock_result.json = '{}'
        
        confidence = transcriber._extract_confidence(mock_result)
        
        assert confidence == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
