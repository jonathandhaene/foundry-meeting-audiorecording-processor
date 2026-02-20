"""
Unit tests for HuggingFace Wav2Vec 2.0 transcriber.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from meeting_processor.transcription.hf_transcriber import HuggingFaceTranscriber


class TestHuggingFaceTranscriberInit:
    """Test HuggingFaceTranscriber initialization."""

    def test_init_api_mode_defaults(self):
        """Test initialization in API mode with default model."""
        transcriber = HuggingFaceTranscriber(use_api=True)

        assert transcriber.model_name == "facebook/wav2vec2-base-960h"
        assert transcriber.use_api is True
        assert transcriber.language is None
        assert transcriber.custom_terms == []

    def test_init_api_mode_custom_model(self):
        """Test initialization in API mode with custom model."""
        transcriber = HuggingFaceTranscriber(
            model_name="facebook/wav2vec2-large-xlsr-53",
            language="en",
            use_api=True,
            api_token="hf_test_token",
            custom_terms=["Azure", "Kubernetes"],
        )

        assert transcriber.model_name == "facebook/wav2vec2-large-xlsr-53"
        assert transcriber.language == "en"
        assert transcriber.use_api is True
        assert transcriber.api_token == "hf_test_token"
        assert transcriber.custom_terms == ["Azure", "Kubernetes"]

    def test_init_with_custom_endpoint(self):
        """Test initialization with a custom Foundry endpoint."""
        endpoint = "https://my-foundry.azureml.net/score"
        transcriber = HuggingFaceTranscriber(endpoint_url=endpoint)

        assert transcriber.endpoint_url == endpoint
        assert transcriber._inference_url == endpoint

    def test_init_api_mode_builds_hf_url(self):
        """Test that API mode builds the HuggingFace Inference API URL."""
        transcriber = HuggingFaceTranscriber(
            model_name="facebook/wav2vec2-base-960h",
            use_api=True,
        )

        assert transcriber._inference_url == "https://api-inference.huggingface.co/models/facebook/wav2vec2-base-960h"

    @patch("meeting_processor.transcription.hf_transcriber.Wav2Vec2Processor", None)
    @patch("meeting_processor.transcription.hf_transcriber.Wav2Vec2ForCTC", None)
    def test_init_local_mode_missing_transformers_raises(self):
        """Test that local mode raises ImportError when transformers is not installed."""
        with pytest.raises(ImportError, match="transformers package is required"):
            HuggingFaceTranscriber(use_api=False)

    @patch("meeting_processor.transcription.hf_transcriber.Wav2Vec2Processor")
    @patch("meeting_processor.transcription.hf_transcriber.Wav2Vec2ForCTC")
    @patch("meeting_processor.transcription.hf_transcriber.torch", None)
    def test_init_local_mode_missing_torch_raises(self, mock_ctc, mock_proc):
        """Test that local mode raises ImportError when torch is not installed."""
        with pytest.raises(ImportError, match="torch package is required"):
            HuggingFaceTranscriber(use_api=False)

    @patch("meeting_processor.transcription.hf_transcriber.httpx", None)
    def test_init_api_mode_missing_httpx_raises(self):
        """Test that API mode raises ImportError when httpx is not installed."""
        with pytest.raises(ImportError, match="httpx package is required"):
            HuggingFaceTranscriber(use_api=True)


class TestHuggingFaceTranscriberAPI:
    """Test HuggingFaceTranscriber remote inference (API mode)."""

    def _make_transcriber(self, model_name="facebook/wav2vec2-base-960h", **kwargs):
        """Helper to build a transcriber in API mode."""
        return HuggingFaceTranscriber(model_name=model_name, use_api=True, **kwargs)

    @patch("meeting_processor.transcription.hf_transcriber.httpx")
    def test_transcribe_api_success(self, mock_httpx):
        """Test successful API transcription returning dict response."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Hello world from Wav2Vec"}

        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        transcriber = self._make_transcriber()

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock(return_value=Mock(read=Mock(return_value=b"fake audio")))
            mock_open.return_value.__exit__ = Mock(return_value=False)
            result = transcriber.transcribe_audio("test.wav")

        assert result.full_text == "Hello world from Wav2Vec"
        assert len(result.segments) == 1
        assert result.segments[0].text == "Hello world from Wav2Vec"
        assert result.metadata["method"] == "huggingface_api"
        assert result.metadata["model"] == "facebook/wav2vec2-base-960h"

    @patch("meeting_processor.transcription.hf_transcriber.httpx")
    def test_transcribe_api_list_response(self, mock_httpx):
        """Test API transcription where response is a list."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = [{"text": "List response text"}]

        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        transcriber = self._make_transcriber()

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock(return_value=Mock(read=Mock(return_value=b"fake audio")))
            mock_open.return_value.__exit__ = Mock(return_value=False)
            result = transcriber.transcribe_audio("test.wav")

        assert result.full_text == "List response text"

    @patch("meeting_processor.transcription.hf_transcriber.httpx")
    def test_transcribe_api_error_raises(self, mock_httpx):
        """Test that non-200 API response raises RuntimeError."""
        mock_response = Mock()
        mock_response.status_code = 503
        mock_response.text = "Service unavailable"

        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        transcriber = self._make_transcriber()

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock(return_value=Mock(read=Mock(return_value=b"fake audio")))
            mock_open.return_value.__exit__ = Mock(return_value=False)
            with pytest.raises(RuntimeError, match="HuggingFace API error"):
                transcriber.transcribe_audio("test.wav")

    @patch("meeting_processor.transcription.hf_transcriber.httpx")
    def test_transcribe_api_sends_auth_header(self, mock_httpx):
        """Test that API token is sent as Authorization header."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Authenticated response"}

        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        transcriber = self._make_transcriber(api_token="hf_secret_token")

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock(return_value=Mock(read=Mock(return_value=b"fake audio")))
            mock_open.return_value.__exit__ = Mock(return_value=False)
            transcriber.transcribe_audio("test.wav")

        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer hf_secret_token"

    @patch("meeting_processor.transcription.hf_transcriber.httpx")
    def test_transcribe_api_empty_text(self, mock_httpx):
        """Test handling of empty transcription from API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": ""}

        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        transcriber = self._make_transcriber()

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock(return_value=Mock(read=Mock(return_value=b"fake audio")))
            mock_open.return_value.__exit__ = Mock(return_value=False)
            result = transcriber.transcribe_audio("test.wav")

        assert result.full_text == ""
        assert result.segments == []

    @patch("meeting_processor.transcription.hf_transcriber.httpx")
    def test_transcribe_api_uses_custom_endpoint(self, mock_httpx):
        """Test that custom endpoint URL is used instead of default HF API."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Foundry result"}

        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        endpoint = "https://my-foundry-endpoint/score"
        transcriber = HuggingFaceTranscriber(endpoint_url=endpoint)

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock(return_value=Mock(read=Mock(return_value=b"fake audio")))
            mock_open.return_value.__exit__ = Mock(return_value=False)
            result = transcriber.transcribe_audio("test.wav")

        call_args = mock_client.post.call_args
        assert call_args[0][0] == endpoint
        assert result.full_text == "Foundry result"
        assert result.metadata["method"] == "huggingface_api"
        assert result.metadata["endpoint"] == endpoint

    @patch("meeting_processor.transcription.hf_transcriber.httpx")
    def test_transcribe_api_metadata_includes_model(self, mock_httpx):
        """Test that metadata includes model name and timestamp."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"text": "Test"}

        mock_client = MagicMock()
        mock_client.__enter__ = Mock(return_value=mock_client)
        mock_client.__exit__ = Mock(return_value=False)
        mock_client.post.return_value = mock_response
        mock_httpx.Client.return_value = mock_client

        model = "facebook/wav2vec2-large-xlsr-53"
        transcriber = self._make_transcriber(model_name=model, custom_terms=["Azure"])

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__ = Mock(return_value=Mock(read=Mock(return_value=b"fake audio")))
            mock_open.return_value.__exit__ = Mock(return_value=False)
            result = transcriber.transcribe_audio("test.wav")

        assert result.metadata["model"] == model
        assert result.metadata["custom_terms_count"] == 1
        assert "timestamp" in result.metadata


class TestHuggingFaceTranscriberLocal:
    """Test HuggingFaceTranscriber local inference mode."""

    @patch("meeting_processor.transcription.hf_transcriber.Wav2Vec2Processor")
    @patch("meeting_processor.transcription.hf_transcriber.Wav2Vec2ForCTC")
    @patch("meeting_processor.transcription.hf_transcriber.torch")
    @patch("meeting_processor.transcription.hf_transcriber.sf")
    def test_transcribe_local_success(self, mock_sf, mock_torch, mock_ctc_class, mock_processor_class):
        """Test successful local transcription."""
        # Mock processor and model
        mock_processor = Mock()
        mock_processor_class.from_pretrained.return_value = mock_processor

        mock_model = Mock()
        mock_ctc_class.from_pretrained.return_value = mock_model

        # Mock audio loading – MagicMock supports len()
        mock_speech = MagicMock()
        mock_speech.ndim = 1
        mock_speech.__len__ = Mock(return_value=16000)
        mock_sf.read.return_value = (mock_speech, 16000)

        # Mock torch operations
        mock_inputs = Mock()
        mock_inputs.input_values = Mock()
        mock_processor.return_value = mock_inputs

        mock_logits = Mock()
        mock_model.return_value = Mock(logits=mock_logits)

        mock_ids = Mock()
        mock_torch.argmax.return_value = mock_ids
        mock_torch.no_grad.return_value.__enter__ = Mock(return_value=None)
        mock_torch.no_grad.return_value.__exit__ = Mock(return_value=False)

        mock_processor.batch_decode.return_value = ["HELLO WORLD"]

        transcriber = HuggingFaceTranscriber(use_api=False)
        result = transcriber.transcribe_audio("test.wav")

        assert result.full_text == "HELLO WORLD"
        assert result.metadata["method"] == "huggingface_local"

    @patch("meeting_processor.transcription.hf_transcriber.Wav2Vec2Processor")
    @patch("meeting_processor.transcription.hf_transcriber.Wav2Vec2ForCTC")
    @patch("meeting_processor.transcription.hf_transcriber.torch")
    @patch("meeting_processor.transcription.hf_transcriber.sf")
    def test_transcribe_local_stereo_to_mono(self, mock_sf, mock_torch, mock_ctc_class, mock_processor_class):
        """Test that stereo audio is converted to mono."""
        mock_processor = Mock()
        mock_processor_class.from_pretrained.return_value = mock_processor

        mock_model = Mock()
        mock_ctc_class.from_pretrained.return_value = mock_model

        # Stereo audio – ndim == 2 triggers the mean() path
        mock_speech = MagicMock()
        mock_speech.ndim = 2
        mono_result = MagicMock()
        mono_result.ndim = 1
        mono_result.__len__ = Mock(return_value=16000)
        mock_speech.mean.return_value = mono_result
        mock_sf.read.return_value = (mock_speech, 16000)

        mock_inputs = Mock()
        mock_inputs.input_values = Mock()
        mock_processor.return_value = mock_inputs

        mock_logits = Mock()
        mock_model.return_value = Mock(logits=mock_logits)

        mock_ids = Mock()
        mock_torch.argmax.return_value = mock_ids
        mock_torch.no_grad.return_value.__enter__ = Mock(return_value=None)
        mock_torch.no_grad.return_value.__exit__ = Mock(return_value=False)

        mock_processor.batch_decode.return_value = ["STEREO TEST"]

        transcriber = HuggingFaceTranscriber(use_api=False)
        result = transcriber.transcribe_audio("test.wav")

        # Verify mean() was called to convert stereo → mono
        mock_speech.mean.assert_called_once_with(axis=1)
        assert result.full_text == "STEREO TEST"


class TestHuggingFaceTranscriberListModels:
    """Test the list_recommended_models static method."""

    def test_list_recommended_models_returns_list(self):
        """Test that list_recommended_models returns a non-empty list."""
        models = HuggingFaceTranscriber.list_recommended_models()

        assert isinstance(models, list)
        assert len(models) > 0

    def test_list_recommended_models_structure(self):
        """Test that each model entry has required fields."""
        models = HuggingFaceTranscriber.list_recommended_models()

        for model in models:
            assert "id" in model
            assert "description" in model
            assert "language" in model

    def test_list_recommended_models_includes_base_english(self):
        """Test that the base English model is in the list."""
        models = HuggingFaceTranscriber.list_recommended_models()
        ids = [m["id"] for m in models]

        assert "facebook/wav2vec2-base-960h" in ids

    def test_list_recommended_models_includes_multilingual(self):
        """Test that a multilingual model is in the list."""
        models = HuggingFaceTranscriber.list_recommended_models()
        multilingual = [m for m in models if m["language"] == "multilingual"]

        assert len(multilingual) > 0
