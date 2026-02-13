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
    with patch('azure.cognitiveservices.speech') as mock_sdk:
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
        with patch.dict('sys.modules', {'azure.cognitiveservices.speech': None}):
            with pytest.raises(Exception):  # Will raise ImportError or AttributeError
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

    def test_custom_terms_initialization(self, mock_speech_sdk):
        """Test transcriber initialization with custom terms."""
        custom_terms = ["Kubernetes", "Azure DevOps", "MLOps"]
        transcriber = AzureSpeechTranscriber(
            speech_key="test_key",
            speech_region="test_region",
            custom_terms=custom_terms
        )
        
        assert transcriber.custom_terms == custom_terms
        assert len(transcriber.custom_terms) == 3

    def test_language_candidates_initialization(self, mock_speech_sdk):
        """Test transcriber initialization with language candidates."""
        language_candidates = ["en-US", "nl-NL"]
        transcriber = AzureSpeechTranscriber(
            speech_key="test_key",
            speech_region="test_region",
            language_candidates=language_candidates
        )
        
        assert transcriber.language_candidates == language_candidates
        assert len(transcriber.language_candidates) == 2

    def test_create_phrase_list(self, transcriber, mock_speech_sdk):
        """Test creating phrase list from custom terms."""
        transcriber.custom_terms = ["term1", "term2", "term3"]
        
        mock_recognizer = Mock()
        mock_phrase_list = Mock()
        mock_speech_sdk.PhraseListGrammar.from_recognizer.return_value = mock_phrase_list
        
        transcriber._create_phrase_list(mock_recognizer)
        
        # Verify phrase list was created from recognizer
        mock_speech_sdk.PhraseListGrammar.from_recognizer.assert_called_once_with(mock_recognizer)
        
        # Verify all terms were added
        assert mock_phrase_list.addPhrase.call_count == 3

    def test_create_phrase_list_empty_terms(self, transcriber):
        """Test creating phrase list with no custom terms."""
        transcriber.custom_terms = []
        
        mock_recognizer = Mock()
        transcriber._create_phrase_list(mock_recognizer)
        
        # Should not raise any errors with empty terms

    def test_setup_auto_detect_language_config(self, transcriber, mock_speech_sdk):
        """Test setting up auto-detect language configuration."""
        transcriber.language_candidates = ["en-US", "nl-NL", "de-DE"]
        
        mock_auto_detect_config = Mock()
        mock_speech_sdk.languageconfig.AutoDetectSourceLanguageConfig.return_value = mock_auto_detect_config
        
        result = transcriber._setup_auto_detect_source_language_config()
        
        assert result == mock_auto_detect_config
        mock_speech_sdk.languageconfig.AutoDetectSourceLanguageConfig.assert_called_once_with(
            languages=["en-US", "nl-NL", "de-DE"]
        )

    def test_setup_auto_detect_language_config_insufficient_languages(self, transcriber):
        """Test auto-detect config returns None with insufficient language candidates."""
        transcriber.language_candidates = ["en-US"]  # Only one language
        
        result = transcriber._setup_auto_detect_source_language_config()
        
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
