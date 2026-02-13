"""
Whisper transcription module using OpenAI's Whisper model.

This module provides an alternative transcription method using
OpenAI's Whisper for local or API-based transcription.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import os

from .transcriber import TranscriptionSegment, TranscriptionResult

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
        api_key: Optional[str] = None
    ):
        """
        Initialize Whisper transcriber.

        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            language: Language code (None for auto-detection)
            use_api: Use OpenAI API instead of local model
            api_key: OpenAI API key (required if use_api=True)
        """
        self.model_size = model_size
        self.language = language
        self.use_api = use_api
        self.api_key = api_key

        if use_api:
            if not api_key:
                raise ValueError("API key required when use_api=True")
            try:
                import openai
                self.openai = openai
                self.openai.api_key = api_key
            except ImportError:
                logger.error("OpenAI package not installed. Install with: pip install openai")
                raise
        else:
            try:
                import whisper
                self.whisper = whisper
                logger.info(f"Loading Whisper model: {model_size}")
                self.model = whisper.load_model(model_size)
            except ImportError:
                logger.error("Whisper package not installed. Install with: pip install openai-whisper")
                raise

    def transcribe_audio(
        self,
        audio_file_path: str,
        chunk_size: Optional[int] = None,
        enable_diarization: bool = False
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

    def _transcribe_local(
        self,
        audio_file_path: str,
        enable_diarization: bool
    ) -> TranscriptionResult:
        """Transcribe using local Whisper model."""
        # Transcribe with word timestamps
        result = self.model.transcribe(
            audio_file_path,
            language=self.language,
            word_timestamps=True,
            verbose=False
        )

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
                confidence=self._calculate_confidence(segment_data)
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
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def _transcribe_with_api(self, audio_file_path: str) -> TranscriptionResult:
        """Transcribe using OpenAI Whisper API."""
        logger.info("Using OpenAI Whisper API")

        with open(audio_file_path, "rb") as audio_file:
            # Call OpenAI API
            if self.language:
                response = self.openai.Audio.transcribe(
                    "whisper-1",
                    audio_file,
                    language=self.language,
                    response_format="verbose_json"
                )
            else:
                response = self.openai.Audio.transcribe(
                    "whisper-1",
                    audio_file,
                    response_format="verbose_json"
                )

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
                confidence=0.0  # API doesn't provide confidence scores
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
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def _calculate_confidence(self, segment_data: Dict[str, Any]) -> float:
        """Calculate average confidence from word-level data."""
        words = segment_data.get("words", [])
        if not words:
            return 0.0
        
        # Average probability of all words in segment
        probabilities = [word.get("probability", 0.0) for word in words]
        return sum(probabilities) / len(probabilities) if probabilities else 0.0
