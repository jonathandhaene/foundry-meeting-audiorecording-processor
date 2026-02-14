"""
Whisper transcription module using OpenAI's Whisper model.

This module provides an alternative transcription method using
OpenAI's Whisper for local or API-based transcription.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from .transcriber import TranscriptionSegment, TranscriptionResult

# Optional imports for Whisper (can be mocked in tests)
try:
    import whisper
except ImportError:
    whisper = None  # type: ignore

try:
    import openai
except ImportError:
    openai = None  # type: ignore

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Handles speech transcription using OpenAI's Whisper.

    Supports:
    - Local model inference
    - OpenAI API integration
    - Multiple languages with auto-detection
    - Word-level timestamps
    """

    def __init__(
        self,
        model_size: str = "base",
        language: Optional[str] = None,
        use_api: bool = False,
        api_key: Optional[str] = None,
        custom_terms: Optional[List[str]] = None,
    ):
        """
        Initialize Whisper transcriber.

        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            language: Language code (None for auto-detection)
            use_api: Use OpenAI API instead of local model
            api_key: OpenAI API key (required if use_api=True)
            custom_terms: List of custom terminology for improved recognition
        """
        self.model_size = model_size
        self.language = language
        self.use_api = use_api
        self.api_key = api_key
        self.custom_terms = custom_terms or []

        if use_api:
            if not api_key:
                raise ValueError("API key required when use_api=True")
            if openai is None:
                logger.error("OpenAI package not installed. Install with: pip install openai")
                raise ImportError("OpenAI package not available")
            self.openai = openai
            self.openai.api_key = api_key
        else:
            if whisper is None:
                logger.error("Whisper package not installed. Install with: pip install openai-whisper")
                raise ImportError("Whisper package not available")
            self.whisper = whisper
            logger.info(f"Loading Whisper model: {model_size}")
            self.model = whisper.load_model(model_size)

    def transcribe_audio(
        self, audio_file_path: str, chunk_size: Optional[int] = None, enable_diarization: bool = False
    ) -> TranscriptionResult:
        """
        Transcribe audio file using Whisper.

        Args:
            audio_file_path: Path to audio file
            chunk_size: Optional chunk size for large files (in seconds)
            enable_diarization: Enable speaker diarization (experimental)

        Returns:
            TranscriptionResult containing transcription and metadata
        """
        logger.info(f"Starting Whisper transcription for: {audio_file_path}")

        if self.use_api:
            return self._transcribe_with_api(audio_file_path)
        else:
            return self._transcribe_local(audio_file_path, enable_diarization)

    def _generate_initial_prompt(self) -> str:
        """
        Generate initial prompt with custom terms for Whisper.

        Whisper uses an initial prompt to guide transcription, which is useful for:
        - Custom terminology and proper nouns
        - Technical jargon
        - Mixed-language contexts

        Returns:
            Initial prompt string containing custom terms
        """
        if not self.custom_terms:
            return ""

        # Create a natural sentence incorporating custom terms
        # This helps Whisper understand these are important terms to recognize
        terms_text = ", ".join(self.custom_terms[:20])  # Limit to avoid token limits
        prompt = f"This transcription may contain the following terms: {terms_text}."

        logger.info(f"Using initial prompt with {len(self.custom_terms)} custom terms")
        return prompt

    def _transcribe_local(self, audio_file_path: str, enable_diarization: bool) -> TranscriptionResult:
        """Transcribe using local Whisper model."""
        # Generate initial prompt with custom terms
        initial_prompt = self._generate_initial_prompt()

        # Transcribe with word timestamps
        transcribe_options = {"language": self.language, "word_timestamps": True, "verbose": False}

        # Add initial prompt if custom terms are provided
        if initial_prompt:
            transcribe_options["initial_prompt"] = initial_prompt

        result = self.model.transcribe(audio_file_path, **transcribe_options)

        segments = []
        full_text_parts = []

        # Process segments
        for segment_data in result.get("segments", []):
            segment = TranscriptionSegment(
                text=segment_data["text"].strip(),
                start_time=segment_data["start"],
                end_time=segment_data["end"],
                speaker_id=None,  # Whisper doesn't provide speaker diarization by default
                language=result.get("language"),
                confidence=self._calculate_confidence(segment_data),
            )
            segments.append(segment)
            full_text_parts.append(segment.text)

        duration = segments[-1].end_time if segments else 0.0

        return TranscriptionResult(
            segments=segments,
            full_text=" ".join(full_text_parts),
            duration=duration,
            language=result.get("language", self.language or "auto"),
            metadata={
                "model": self.model_size,
                "method": "whisper_local",
                "diarization_enabled": False,
                "custom_terms_count": len(self.custom_terms),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _transcribe_with_api(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe using OpenAI Whisper API."""
        logger.info("Using OpenAI Whisper API")

        # Generate initial prompt with custom terms
        initial_prompt = self._generate_initial_prompt()

        with open(audio_file_path, "rb") as audio_file:
            # Call OpenAI API with optional custom prompt
            api_params = {"model": "whisper-1", "file": audio_file, "response_format": "verbose_json"}

            if self.language:
                api_params["language"] = self.language

            if initial_prompt:
                api_params["prompt"] = initial_prompt

            response = self.openai.Audio.transcribe(**api_params)

        segments = []
        full_text_parts = []

        # Process API response segments
        for segment_data in response.get("segments", []):
            segment = TranscriptionSegment(
                text=segment_data["text"].strip(),
                start_time=segment_data["start"],
                end_time=segment_data["end"],
                speaker_id=None,
                language=response.get("language"),
                confidence=0.0,  # API doesn't provide confidence scores
            )
            segments.append(segment)
            full_text_parts.append(segment.text)

        duration = response.get("duration", 0.0)

        return TranscriptionResult(
            segments=segments,
            full_text=response.get("text", " ".join(full_text_parts)),
            duration=duration,
            language=response.get("language", self.language or "auto"),
            metadata={
                "model": "whisper-1",
                "method": "whisper_api",
                "diarization_enabled": False,
                "custom_terms_count": len(self.custom_terms),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _calculate_confidence(self, segment_data: Dict[str, Any]) -> float:
        """Calculate average confidence from word-level data."""
        words = segment_data.get("words", [])
        if not words:
            return 0.0

        # Average probability of all words in segment
        probabilities = [word.get("probability", 0.0) for word in words]
        return sum(probabilities) / len(probabilities) if probabilities else 0.0
