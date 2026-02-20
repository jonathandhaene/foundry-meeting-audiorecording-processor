"""
Hugging Face Wav2Vec 2.0 transcription module.

This module provides speech-to-text transcription using Hugging Face's
Wav2Vec 2.0 models. Supports local inference via the transformers library
and remote inference via the Hugging Face Inference API or a custom
Foundry-deployed endpoint.
"""

import logging
import os
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from .transcriber import TranscriptionSegment, TranscriptionResult

# Optional imports for local inference (transformers + torch)
try:
    from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
except ImportError:
    Wav2Vec2Processor = None  # type: ignore
    Wav2Vec2ForCTC = None  # type: ignore

try:
    import torch
except ImportError:
    torch = None  # type: ignore

# Optional import for audio loading
try:
    import soundfile as sf
except ImportError:
    sf = None  # type: ignore

# httpx is already in requirements.txt (used by AzureSpeechTranscriber)
try:
    import httpx
except ImportError:
    httpx = None  # type: ignore

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "facebook/wav2vec2-base-960h"
SAMPLE_RATE = 16000


class HuggingFaceTranscriber:
    """
    Handles speech transcription using Hugging Face Wav2Vec 2.0.

    Supports:
    - Local model inference using the transformers library
    - Hugging Face Inference API
    - Custom endpoint (e.g., deployed via Microsoft Foundry)
    - Pre-trained and fine-tuned Wav2Vec 2.0 models
    """

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        language: Optional[str] = None,
        use_api: bool = False,
        api_token: Optional[str] = None,
        endpoint_url: Optional[str] = None,
        custom_terms: Optional[List[str]] = None,
    ):
        """
        Initialize HuggingFace Wav2Vec 2.0 transcriber.

        Args:
            model_name: HuggingFace model identifier (e.g., 'facebook/wav2vec2-base-960h',
                        'facebook/wav2vec2-large-960h-lv60-self')
            language: Language hint (informational; the model is language-specific)
            use_api: Use HuggingFace Inference API or custom endpoint instead of local model
            api_token: HuggingFace API token (required for private models or rate-limit bypass)
            endpoint_url: Custom inference endpoint URL (e.g., Foundry-deployed server).
                          Overrides the default HF Inference API URL.
            custom_terms: List of custom terminology for post-processing hints
        """
        self.model_name = model_name
        self.language = language
        self.use_api = use_api
        self.api_token = api_token or os.environ.get("HUGGINGFACE_API_TOKEN")
        self.endpoint_url = endpoint_url or os.environ.get("HUGGINGFACE_ENDPOINT_URL")
        self.custom_terms = custom_terms or []

        if use_api or self.endpoint_url:
            # Remote inference mode – only needs httpx (already in requirements)
            if httpx is None:
                raise ImportError("httpx package is required for remote inference. Install with: pip install httpx")
            self._inference_url = self.endpoint_url or f"https://api-inference.huggingface.co/models/{model_name}"
            logger.info(f"HuggingFace transcriber using remote endpoint: {self._inference_url}")
        else:
            # Local inference mode – requires transformers + torch + soundfile
            if Wav2Vec2Processor is None or Wav2Vec2ForCTC is None:
                raise ImportError(
                    "transformers package is required for local Wav2Vec 2.0 inference. "
                    "Install with: pip install transformers>=4.48.0"
                )
            if torch is None:
                raise ImportError(
                    "torch package is required for local Wav2Vec 2.0 inference. " "Install with: pip install torch>=2.6.0"
                )
            if sf is None:
                raise ImportError(
                    "soundfile package is required for local Wav2Vec 2.0 inference. " "Install with: pip install soundfile"
                )
            logger.info(f"Loading Wav2Vec2 model: {model_name}")
            self.processor = Wav2Vec2Processor.from_pretrained(model_name)
            self.model = Wav2Vec2ForCTC.from_pretrained(model_name)
            self.model.eval()
            logger.info(f"Wav2Vec2 model loaded: {model_name}")

    def transcribe_audio(self, audio_file_path: str) -> TranscriptionResult:
        """
        Transcribe audio file using Wav2Vec 2.0.

        Args:
            audio_file_path: Path to audio file (WAV, 16kHz mono recommended)

        Returns:
            TranscriptionResult containing transcription and metadata
        """
        logger.info(f"Starting HuggingFace transcription for: {audio_file_path}")

        if self.use_api or self.endpoint_url:
            return self._transcribe_with_api(audio_file_path)
        else:
            return self._transcribe_local(audio_file_path)

    def _transcribe_local(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe using local Wav2Vec 2.0 model."""
        # Load audio with soundfile
        speech, sample_rate = sf.read(audio_file_path)

        # Convert stereo to mono if needed
        if speech.ndim > 1:
            speech = speech.mean(axis=1)

        # Resample to 16 kHz if needed
        if sample_rate != SAMPLE_RATE:
            try:
                import librosa  # optional – only needed when resampling is required

                speech = librosa.resample(speech, orig_sr=sample_rate, target_sr=SAMPLE_RATE)
                sample_rate = SAMPLE_RATE
            except ImportError:
                logger.warning(
                    "librosa is not installed; audio resampling skipped. "
                    "Results may be degraded if sample rate is not 16 kHz."
                )

        duration = len(speech) / SAMPLE_RATE

        # Process audio through Wav2Vec 2.0
        inputs = self.processor(speech, sampling_rate=SAMPLE_RATE, return_tensors="pt", padding=True)

        with torch.no_grad():
            logits = self.model(inputs.input_values).logits

        # Greedy decode
        predicted_ids = torch.argmax(logits, dim=-1)
        transcription = self.processor.batch_decode(predicted_ids)[0]

        # Wav2Vec 2.0 does not produce per-segment timestamps natively;
        # a single segment spanning the entire file is returned.
        text = transcription.strip()
        segment = TranscriptionSegment(
            text=text,
            start_time=0.0,
            end_time=duration,
            speaker_id=None,
            language=self.language,
            confidence=0.0,
        )

        return TranscriptionResult(
            segments=[segment] if text else [],
            full_text=text,
            duration=duration,
            language=self.language or "auto",
            metadata={
                "model": self.model_name,
                "method": "huggingface_local",
                "custom_terms_count": len(self.custom_terms),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _transcribe_with_api(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe using HuggingFace Inference API or a custom (Foundry) endpoint."""
        headers: Dict[str, str] = {"Content-Type": "application/octet-stream"}
        if self.api_token:
            headers["Authorization"] = f"Bearer {self.api_token}"

        with open(audio_file_path, "rb") as audio_file:
            audio_data = audio_file.read()

        file_size = len(audio_data)
        logger.info(f"Sending {file_size / 1024:.1f} KB to HuggingFace endpoint: {self._inference_url}")

        with httpx.Client(timeout=300.0) as client:
            response = client.post(
                self._inference_url,
                headers=headers,
                content=audio_data,
            )

        if response.status_code != 200:
            logger.error(f"HuggingFace API error ({response.status_code}): {response.text[:500]}")
            raise RuntimeError(f"HuggingFace API error ({response.status_code}): {response.text[:300]}")

        result = response.json()

        # HF Inference API returns {"text": "..."} for ASR tasks
        transcription = ""
        if isinstance(result, dict):
            transcription = result.get("text", "")
        elif isinstance(result, list) and result:
            transcription = result[0].get("text", "") if isinstance(result[0], dict) else str(result[0])

        text = transcription.strip()
        segment = TranscriptionSegment(
            text=text,
            start_time=0.0,
            end_time=0.0,
            speaker_id=None,
            language=self.language,
            confidence=0.0,
        )

        return TranscriptionResult(
            segments=[segment] if text else [],
            full_text=text,
            duration=0.0,
            language=self.language or "auto",
            metadata={
                "model": self.model_name,
                "method": "huggingface_api",
                "endpoint": self._inference_url,
                "custom_terms_count": len(self.custom_terms),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def list_recommended_models() -> List[Dict[str, Any]]:
        """
        Return a curated list of recommended Wav2Vec 2.0 models.

        These models are available on the HuggingFace Model Hub and cover
        a range of languages and accuracy/speed trade-offs.
        """
        return [
            {
                "id": "facebook/wav2vec2-base-960h",
                "description": "Base English model (LibriSpeech 960h)",
                "language": "en",
                "size": "~360 MB",
            },
            {
                "id": "facebook/wav2vec2-large-960h-lv60-self",
                "description": "Large English model – high accuracy",
                "language": "en",
                "size": "~1.18 GB",
            },
            {
                "id": "facebook/wav2vec2-large-xlsr-53",
                "description": "Multilingual XLSR-53 model (53 languages)",
                "language": "multilingual",
                "size": "~1.18 GB",
            },
            {
                "id": "facebook/wav2vec2-base",
                "description": "Base model for fine-tuning",
                "language": "en",
                "size": "~360 MB",
            },
        ]
