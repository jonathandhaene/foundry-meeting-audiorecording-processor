"""
Speech transcription module using Azure Speech Services.

This module handles speech-to-text transcription with support for
speaker diarization and multilingual content.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class TranscriptionSegment:
    """Represents a single segment of transcribed text."""
    text: str
    start_time: float
    end_time: float
    speaker_id: Optional[str] = None
    language: Optional[str] = None
    confidence: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)


@dataclass
class TranscriptionResult:
    """Complete transcription result with metadata."""
    segments: List[TranscriptionSegment]
    full_text: str
    duration: float
    language: str
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "segments": [seg.to_dict() for seg in self.segments],
            "full_text": self.full_text,
            "duration": self.duration,
            "language": self.language,
            "metadata": self.metadata
        }


class AzureSpeechTranscriber:
    """
    Handles speech transcription using Azure Speech Services.
    
    Supports:
    - Speech-to-text transcription
    - Speaker diarization
    - Multiple languages
    - Real-time and batch processing
    """

    def __init__(
        self,
        speech_key: str,
        speech_region: str,
        language: str = "en-US",
        enable_diarization: bool = True,
        max_speakers: int = 10
    ):
        """
        Initialize Azure Speech transcriber.

        Args:
            speech_key: Azure Speech Services API key
            speech_region: Azure region (e.g., 'eastus')
            language: Primary language code (e.g., 'en-US')
            enable_diarization: Enable speaker diarization
            max_speakers: Maximum number of speakers to identify
        """
        self.speech_key = speech_key
        self.speech_region = speech_region
        self.language = language
        self.enable_diarization = enable_diarization
        self.max_speakers = max_speakers

        try:
            import azure.cognitiveservices.speech as speechsdk
            self.speechsdk = speechsdk
            self._initialize_config()
        except ImportError:
            logger.error("Azure Speech SDK not installed. Install with: pip install azure-cognitiveservices-speech")
            raise

    def _initialize_config(self) -> None:
        """Initialize Azure Speech configuration."""
        self.speech_config = self.speechsdk.SpeechConfig(
            subscription=self.speech_key,
            region=self.speech_region
        )
        self.speech_config.speech_recognition_language = self.language

        # Enable detailed output
        self.speech_config.output_format = self.speechsdk.OutputFormat.Detailed
        
        # Request word-level timestamps
        self.speech_config.request_word_level_timestamps()

    def transcribe_audio(
        self,
        audio_file_path: str,
        languages: Optional[List[str]] = None
    ) -> TranscriptionResult:
        """
        Transcribe audio file using Azure Speech Services.

        Args:
            audio_file_path: Path to audio file
            languages: List of language codes for multi-language support

        Returns:
            TranscriptionResult containing transcription and metadata
        """
        logger.info(f"Starting transcription for: {audio_file_path}")

        # Create audio config
        audio_config = self.speechsdk.audio.AudioConfig(filename=audio_file_path)

        # Set up conversation transcriber for diarization if enabled
        if self.enable_diarization:
            return self._transcribe_with_diarization(audio_file_path, audio_config)
        else:
            return self._transcribe_basic(audio_config)

    def _transcribe_basic(self, audio_config) -> TranscriptionResult:
        """Basic transcription without speaker diarization."""
        speech_recognizer = self.speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )

        segments = []
        full_text_parts = []
        done = False

        def recognized_cb(evt):
            if evt.result.reason == self.speechsdk.ResultReason.RecognizedSpeech:
                result = evt.result
                segment = TranscriptionSegment(
                    text=result.text,
                    start_time=result.offset / 10000000.0,  # Convert to seconds
                    end_time=(result.offset + result.duration) / 10000000.0,
                    confidence=self._extract_confidence(result)
                )
                segments.append(segment)
                full_text_parts.append(result.text)
                logger.debug(f"Recognized: {result.text}")

        def stop_cb(evt):
            nonlocal done
            done = True
            logger.info("Transcription completed")

        speech_recognizer.recognized.connect(recognized_cb)
        speech_recognizer.session_stopped.connect(stop_cb)
        speech_recognizer.canceled.connect(stop_cb)

        speech_recognizer.start_continuous_recognition()

        # Wait for completion
        import time
        while not done:
            time.sleep(0.5)

        speech_recognizer.stop_continuous_recognition()

        duration = segments[-1].end_time if segments else 0.0

        return TranscriptionResult(
            segments=segments,
            full_text=" ".join(full_text_parts),
            duration=duration,
            language=self.language,
            metadata={
                "diarization_enabled": False,
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def _transcribe_with_diarization(
        self,
        audio_file_path: str,
        audio_config
    ) -> TranscriptionResult:
        """Transcription with speaker diarization."""
        # Create conversation transcriber
        conversation_transcriber = self.speechsdk.transcription.ConversationTranscriber(
            speech_config=self.speech_config,
            audio_config=audio_config
        )

        segments = []
        full_text_parts = []
        done = False

        def transcribed_cb(evt):
            if evt.result.reason == self.speechsdk.ResultReason.RecognizedSpeech:
                result = evt.result
                segment = TranscriptionSegment(
                    text=result.text,
                    start_time=result.offset / 10000000.0,
                    end_time=(result.offset + result.duration) / 10000000.0,
                    speaker_id=result.speaker_id,
                    confidence=self._extract_confidence(result)
                )
                segments.append(segment)
                full_text_parts.append(result.text)
                logger.debug(f"Speaker {result.speaker_id}: {result.text}")

        def stop_cb(evt):
            nonlocal done
            done = True
            logger.info("Diarized transcription completed")

        conversation_transcriber.transcribed.connect(transcribed_cb)
        conversation_transcriber.session_stopped.connect(stop_cb)
        conversation_transcriber.canceled.connect(stop_cb)

        conversation_transcriber.start_transcribing_async().get()

        # Wait for completion
        import time
        while not done:
            time.sleep(0.5)

        conversation_transcriber.stop_transcribing_async().get()

        duration = segments[-1].end_time if segments else 0.0

        # Count unique speakers
        speakers = set(seg.speaker_id for seg in segments if seg.speaker_id)

        return TranscriptionResult(
            segments=segments,
            full_text=" ".join(full_text_parts),
            duration=duration,
            language=self.language,
            metadata={
                "diarization_enabled": True,
                "speaker_count": len(speakers),
                "speakers": list(speakers),
                "timestamp": datetime.utcnow().isoformat()
            }
        )

    def _extract_confidence(self, result) -> float:
        """Extract confidence score from recognition result."""
        try:
            import json
            details = json.loads(result.json)
            nbest = details.get("NBest", [])
            if nbest:
                return nbest[0].get("Confidence", 0.0)
        except Exception:
            pass
        return 0.0

    def transcribe_realtime(self, audio_stream):
        """
        Transcribe audio in real-time from a stream.
        
        This is a placeholder for real-time transcription functionality.
        """
        raise NotImplementedError("Real-time transcription not yet implemented")
