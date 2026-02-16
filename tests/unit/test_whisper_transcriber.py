"""
Unit tests for Whisper transcriber.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from meeting_processor.transcription.whisper_transcriber import WhisperTranscriber


class TestWhisperTranscriber:
    """Test Whisper transcription functionality."""

    @patch("meeting_processor.transcription.whisper_transcriber.whisper")
    def test_init_local_model(self, mock_whisper):
        """Test initialization with local model."""
        mock_whisper.load_model.return_value = Mock()

        transcriber = WhisperTranscriber(model_size="base", language="en", use_api=False)

        assert transcriber.model_size == "base"
        assert transcriber.language == "en"
        assert transcriber.use_api is False
        mock_whisper.load_model.assert_called_once_with("base")

    @patch("meeting_processor.transcription.whisper_transcriber.openai")
    def test_init_api_model(self, mock_openai):
        """Test initialization with API."""
        transcriber = WhisperTranscriber(language="es", use_api=True, api_key="test_key")

        assert transcriber.use_api is True
        assert transcriber.api_key == "test_key"
        assert transcriber.language == "es"

    def test_init_api_without_key_raises_error(self):
        """Test that API mode without key raises error."""
        with pytest.raises(ValueError, match="API key required"):
            WhisperTranscriber(use_api=True, api_key=None)

    @patch("meeting_processor.transcription.whisper_transcriber.whisper")
    def test_transcribe_local(self, mock_whisper):
        """Test local transcription."""
        # Setup mock model and result
        mock_model = Mock()
        mock_result = {
            "text": "Hello world",
            "language": "en",
            "segments": [
                {
                    "text": "Hello world",
                    "start": 0.0,
                    "end": 2.0,
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 1.0, "probability": 0.95},
                        {"word": "world", "start": 1.0, "end": 2.0, "probability": 0.92},
                    ],
                }
            ],
        }
        mock_model.transcribe.return_value = mock_result
        mock_whisper.load_model.return_value = mock_model

        transcriber = WhisperTranscriber(model_size="base", use_api=False)
        result = transcriber.transcribe_audio("test.wav")

        # Verify transcription result
        assert result.full_text == "Hello world"
        assert result.language == "en"
        assert len(result.segments) == 1
        assert result.segments[0].text == "Hello world"
        assert result.segments[0].start_time == 0.0
        assert result.segments[0].end_time == 2.0
        assert result.metadata["method"] == "whisper_local"
        assert result.metadata["model"] == "base"

    @patch("meeting_processor.transcription.whisper_transcriber.whisper")
    def test_transcribe_with_language(self, mock_whisper):
        """Test transcription with specified language."""
        mock_model = Mock()
        mock_result = {
            "text": "Hola mundo",
            "language": "es",
            "segments": [{"text": "Hola mundo", "start": 0.0, "end": 1.5, "words": []}],
        }
        mock_model.transcribe.return_value = mock_result
        mock_whisper.load_model.return_value = mock_model

        transcriber = WhisperTranscriber(model_size="base", language="es", use_api=False)
        result = transcriber.transcribe_audio("test.wav")

        # Verify language was passed
        mock_model.transcribe.assert_called_once()
        call_args = mock_model.transcribe.call_args
        assert call_args[1]["language"] == "es"
        assert result.language == "es"

    @patch("meeting_processor.transcription.whisper_transcriber.openai")
    def test_transcribe_api(self, mock_openai):
        """Test API-based transcription."""
        # Setup mock API response
        mock_response = {
            "text": "API transcription result",
            "language": "en",
            "duration": 5.0,
            "segments": [{"text": "API transcription result", "start": 0.0, "end": 5.0}],
        }
        mock_openai.Audio.transcribe.return_value = mock_response

        transcriber = WhisperTranscriber(use_api=True, api_key="test_key")

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = Mock()
            result = transcriber.transcribe_audio("test.wav")

        # Verify API was called
        assert mock_openai.Audio.transcribe.called
        assert result.full_text == "API transcription result"
        assert result.duration == 5.0
        assert result.metadata["method"] == "whisper_api"

    @patch("meeting_processor.transcription.whisper_transcriber.whisper")
    def test_calculate_confidence(self, mock_whisper):
        """Test confidence calculation from word probabilities."""
        mock_model = Mock()
        mock_result = {
            "text": "Test",
            "language": "en",
            "segments": [
                {
                    "text": "Test",
                    "start": 0.0,
                    "end": 1.0,
                    "words": [{"word": "Test", "start": 0.0, "end": 1.0, "probability": 0.9}],
                }
            ],
        }
        mock_model.transcribe.return_value = mock_result
        mock_whisper.load_model.return_value = mock_model

        transcriber = WhisperTranscriber(model_size="base", use_api=False)
        result = transcriber.transcribe_audio("test.wav")

        # Check that confidence was calculated
        assert result.segments[0].confidence > 0

    @patch("meeting_processor.transcription.whisper_transcriber.whisper")
    def test_transcribe_empty_result(self, mock_whisper):
        """Test handling of empty transcription result."""
        mock_model = Mock()
        mock_result = {"text": "", "language": "en", "segments": []}
        mock_model.transcribe.return_value = mock_result
        mock_whisper.load_model.return_value = mock_model

        transcriber = WhisperTranscriber(model_size="base", use_api=False)
        result = transcriber.transcribe_audio("test.wav")

        assert result.full_text == ""
        assert len(result.segments) == 0
        assert result.duration == 0.0

    @patch("meeting_processor.transcription.whisper_transcriber.openai")
    def test_transcribe_api_with_language(self, mock_openai):
        """Test API transcription with language specification."""
        mock_response = {"text": "Bonjour", "language": "fr", "duration": 1.0, "segments": []}
        mock_openai.Audio.transcribe.return_value = mock_response

        transcriber = WhisperTranscriber(language="fr", use_api=True, api_key="test_key")

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = Mock()
            result = transcriber.transcribe_audio("test.wav")

        # Verify language was passed to API
        call_args = mock_openai.Audio.transcribe.call_args
        assert call_args[1]["language"] == "fr"
        assert result.language == "fr"

    @patch("meeting_processor.transcription.whisper_transcriber.whisper", create=True)
    def test_custom_terms_initialization(self, mock_whisper):
        """Test initialization with custom terms."""
        mock_whisper.load_model.return_value = Mock()

        custom_terms = ["Kubernetes", "MLOps", "Azure"]
        transcriber = WhisperTranscriber(model_size="base", custom_terms=custom_terms, use_api=False)

        assert transcriber.custom_terms == custom_terms
        assert len(transcriber.custom_terms) == 3

    @patch("meeting_processor.transcription.whisper_transcriber.whisper", create=True)
    def test_generate_initial_prompt(self, mock_whisper):
        """Test generating initial prompt from custom terms."""
        mock_whisper.load_model.return_value = Mock()

        custom_terms = ["Docker", "Kubernetes", "Terraform"]
        transcriber = WhisperTranscriber(model_size="base", custom_terms=custom_terms, use_api=False)

        prompt = transcriber._generate_initial_prompt()

        assert "Docker" in prompt
        assert "Kubernetes" in prompt
        assert "Terraform" in prompt
        assert len(prompt) > 0

    @patch("meeting_processor.transcription.whisper_transcriber.whisper", create=True)
    def test_generate_initial_prompt_empty(self, mock_whisper):
        """Test generating initial prompt with no custom terms."""
        mock_whisper.load_model.return_value = Mock()

        transcriber = WhisperTranscriber(model_size="base", custom_terms=[], use_api=False)

        prompt = transcriber._generate_initial_prompt()

        assert prompt == ""

    @patch("meeting_processor.transcription.whisper_transcriber.whisper", create=True)
    def test_transcribe_with_custom_terms(self, mock_whisper):
        """Test transcription with custom terms."""
        mock_model = Mock()
        mock_result = {
            "text": "Using Kubernetes and Docker",
            "language": "en",
            "segments": [{"text": "Using Kubernetes and Docker", "start": 0.0, "end": 3.0, "words": []}],
        }
        mock_model.transcribe.return_value = mock_result
        mock_whisper.load_model.return_value = mock_model

        custom_terms = ["Kubernetes", "Docker"]
        transcriber = WhisperTranscriber(model_size="base", custom_terms=custom_terms, use_api=False)
        result = transcriber.transcribe_audio("test.wav")

        # Verify custom terms were used in initial prompt
        call_args = mock_model.transcribe.call_args
        assert "initial_prompt" in call_args[1]
        assert "Kubernetes" in call_args[1]["initial_prompt"]
        assert "Docker" in call_args[1]["initial_prompt"]

        # Verify metadata includes custom terms count
        assert result.metadata["custom_terms_count"] == 2

    @patch("meeting_processor.transcription.whisper_transcriber.openai", create=True)
    def test_transcribe_api_with_custom_terms(self, mock_openai):
        """Test API transcription with custom terms."""
        mock_response = {"text": "Using Azure DevOps", "language": "en", "duration": 2.0, "segments": []}
        mock_openai.Audio.transcribe.return_value = mock_response

        custom_terms = ["Azure DevOps"]
        transcriber = WhisperTranscriber(custom_terms=custom_terms, use_api=True, api_key="test_key")

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = Mock()
            result = transcriber.transcribe_audio("test.wav")

        # Verify prompt parameter was passed to API
        call_args = mock_openai.Audio.transcribe.call_args
        assert "prompt" in call_args[1]
        assert "Azure DevOps" in call_args[1]["prompt"]

        # Verify metadata includes custom terms count
        assert result.metadata["custom_terms_count"] == 1
