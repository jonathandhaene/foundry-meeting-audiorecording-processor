"""
Speech transcription module using Azure Speech Services.

This module handles speech-to-text transcription with support for
speaker diarization and multilingual content.
"""

import logging
import json
import os
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

# Azure Speech SDK imports (can be mocked in tests)
try:
    import azure.cognitiveservices.speech as speechsdk
except ImportError:
    speechsdk = None  # type: ignore

try:
    from azure.identity import DefaultAzureCredential
except ImportError:
    DefaultAzureCredential = None  # type: ignore

logger = logging.getLogger(__name__)


def _parse_iso_duration(iso_str) -> float:
    """Parse ISO 8601 duration string (e.g. PT15.34S, PT1M30.5S) to seconds.
    Also handles numeric values (seconds as float/int) and HH:MM:SS formats."""
    if iso_str is None:
        return 0.0
    # If it's already a number, return it directly (seconds)
    if isinstance(iso_str, (int, float)):
        return float(iso_str)
    iso_str = str(iso_str).strip()
    if not iso_str:
        return 0.0
    # Try ISO 8601 duration format first: PT1H2M3.4S
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:([\d.]+)S)?", iso_str)
    if m and m.group(0) != "PT":  # Ensure something was matched beyond "PT"
        hours = float(m.group(1) or 0)
        minutes = float(m.group(2) or 0)
        seconds = float(m.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds
    # Try HH:MM:SS.mmm format
    m2 = re.match(r"(\d+):(\d+):(\d+(?:\.\d+)?)", iso_str)
    if m2:
        return float(m2.group(1)) * 3600 + float(m2.group(2)) * 60 + float(m2.group(3))
    # Try plain number (seconds)
    try:
        return float(iso_str)
    except (ValueError, TypeError):
        logger.warning(f"Could not parse duration value: {iso_str!r}")
        return 0.0


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
            "metadata": self.metadata,
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
        speech_key: Optional[str] = None,
        speech_region: str = "eastus",
        language: str = "en-US",
        enable_diarization: bool = True,
        max_speakers: int = 10,
        custom_terms: Optional[List[str]] = None,
        language_candidates: Optional[List[str]] = None,
        use_managed_identity: bool = False,
        speech_resource_id: Optional[str] = None,
        speech_endpoint: Optional[str] = None,
        profanity_filter: Optional[str] = None,
        word_level_timestamps: bool = False,
    ):
        """
        Initialize Azure Speech transcriber.

        Args:
            speech_key: Azure Speech Services API key (optional if using managed identity)
            speech_region: Azure region (e.g., 'eastus')
            language: Primary language code (e.g., 'en-US')
            enable_diarization: Enable speaker diarization
            max_speakers: Maximum number of speakers to identify
            custom_terms: List of custom terminology for improved recognition
            language_candidates: List of language codes for multi-language support (e.g., ['en-US', 'nl-NL'])
            use_managed_identity: Use Azure AD managed identity instead of API key
            speech_resource_id: Azure Resource Manager resource ID for AAD auth
            speech_endpoint: Custom subdomain endpoint (e.g., https://<name>.cognitiveservices.azure.com/)
            profanity_filter: Profanity filter mode ('masked', 'removed', 'raw', None)
            word_level_timestamps: Enable word-level timestamps
        """
        self.speech_key = speech_key
        self.speech_region = speech_region
        self.use_managed_identity = use_managed_identity
        self.speech_resource_id = speech_resource_id
        self.speech_endpoint = speech_endpoint
        self.language = language
        self.enable_diarization = enable_diarization
        self.max_speakers = max_speakers
        self.custom_terms = custom_terms or []
        self.language_candidates = language_candidates or []
        self.profanity_filter = profanity_filter
        self.word_level_timestamps = word_level_timestamps

        if speechsdk is None:
            logger.error("Azure Speech SDK not installed. Install with: pip install azure-cognitiveservices-speech")
            raise ImportError("azure-cognitiveservices-speech package is required but not installed")

        self.speechsdk = speechsdk
        self._initialize_config()

    def _initialize_config(self) -> None:
        """Initialize Azure Speech configuration."""
        if self.use_managed_identity:
            if DefaultAzureCredential is None:
                raise ImportError("azure-identity package is required for managed identity auth")
            self._credential = DefaultAzureCredential()
            token = self._credential.get_token("https://cognitiveservices.azure.com/.default")
            # Speech SDK AAD auth requires: aad#{ARM_RESOURCE_ID}#{AAD_TOKEN}
            if not self.speech_resource_id:
                raise ValueError(
                    "speech_resource_id is required for managed identity auth. "
                    "Set AZURE_SPEECH_RESOURCE_ID environment variable."
                )
            auth_token = f"aad#{self.speech_resource_id}#{token.token}"
            self.speech_config = self.speechsdk.SpeechConfig(
                auth_token=auth_token, region=self.speech_region
            )
            logger.info(f"Using Azure AD managed identity for Speech Services (resource: {self.speech_resource_id})")
        else:
            self.speech_config = self.speechsdk.SpeechConfig(
                subscription=self.speech_key, region=self.speech_region
            )
        self.speech_config.speech_recognition_language = self.language

        # Enable detailed output
        self.speech_config.output_format = self.speechsdk.OutputFormat.Detailed

        # Request word-level timestamps if enabled
        if self.word_level_timestamps:
            self.speech_config.request_word_level_timestamps()

        # Apply profanity filter setting
        if self.profanity_filter:
            profanity_modes = {
                "masked": self.speechsdk.ProfanityOption.Masked,
                "removed": self.speechsdk.ProfanityOption.Removed,
                "raw": self.speechsdk.ProfanityOption.Raw,
            }
            mode = profanity_modes.get(self.profanity_filter.lower())
            if mode is not None:
                self.speech_config.set_profanity(mode)
                logger.info(f"Profanity filter set to: {self.profanity_filter}")

    def _create_phrase_list(self, recognizer) -> None:
        """
        Create and apply phrase list grammar for custom terminology.

        Args:
            recognizer: Speech recognizer or conversation transcriber instance
        """
        if not self.custom_terms:
            return

        try:
            # Create phrase list grammar
            phrase_list_grammar = self.speechsdk.PhraseListGrammar.from_recognizer(recognizer)

            # Add custom terms to phrase list
            for term in self.custom_terms:
                if term and term.strip():
                    phrase_list_grammar.addPhrase(term.strip())
                    logger.debug(f"Added custom term to phrase list: {term.strip()}")

            logger.info(f"Applied {len(self.custom_terms)} custom terms to phrase list")
        except Exception as e:
            logger.warning(f"Failed to create phrase list: {e}")

    def _setup_auto_detect_source_language_config(self):
        """
        Set up automatic language detection configuration for multi-language support.

        Returns:
            AutoDetectSourceLanguageConfig if language candidates are provided, None otherwise
        """
        if not self.language_candidates or len(self.language_candidates) < 2:
            return None

        try:
            auto_detect_config = self.speechsdk.languageconfig.AutoDetectSourceLanguageConfig(
                languages=self.language_candidates
            )
            logger.info(f"Enabled multi-language detection for: {', '.join(self.language_candidates)}")
            return auto_detect_config
        except Exception as e:
            logger.warning(f"Failed to setup auto-detect language config: {e}")
            return None

    def transcribe_audio(self, audio_file_path: str, languages: Optional[List[str]] = None, progress_callback=None) -> TranscriptionResult:
        """
        Transcribe audio file using Azure Speech Services.

        Args:
            audio_file_path: Path to audio file
            languages: List of language codes for multi-language support
            progress_callback: Optional callable(segments_count) called when new segments are recognized

        Returns:
            TranscriptionResult containing transcription and metadata
        """
        logger.info(f"Starting transcription for: {audio_file_path}")

        # Create audio config
        audio_config = self.speechsdk.audio.AudioConfig(filename=audio_file_path)

        # Set up conversation transcriber for diarization if enabled
        if self.enable_diarization:
            return self._transcribe_with_diarization(audio_file_path, audio_config, progress_callback=progress_callback)
        else:
            return self._transcribe_basic(audio_config, progress_callback=progress_callback)

    def _transcribe_basic(self, audio_config, progress_callback=None) -> TranscriptionResult:
        """Basic transcription without speaker diarization."""
        # Set up multi-language detection if configured
        auto_detect_config = self._setup_auto_detect_source_language_config()

        if auto_detect_config:
            speech_recognizer = self.speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config,
                auto_detect_source_language_config=auto_detect_config,
            )
        else:
            speech_recognizer = self.speechsdk.SpeechRecognizer(speech_config=self.speech_config, audio_config=audio_config)

        # Apply custom phrase list for improved recognition
        self._create_phrase_list(speech_recognizer)

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
                    confidence=self._extract_confidence(result),
                )
                segments.append(segment)
                full_text_parts.append(result.text)
                logger.debug(f"Recognized: {result.text}")
                if progress_callback:
                    try:
                        progress_callback(len(segments))
                    except Exception:
                        pass

        cancellation_error = None

        def stop_cb(evt):
            nonlocal done
            done = True
            logger.info("Transcription session stopped")

        def canceled_cb(evt):
            nonlocal done, cancellation_error
            done = True
            cancellation = evt.result.cancellation_details
            logger.warning(f"Transcription canceled: {cancellation.reason}")
            if cancellation.reason == self.speechsdk.CancellationReason.Error:
                cancellation_error = f"Speech service error: {cancellation.error_details}"
                logger.error(f"Cancellation error: {cancellation.error_details}")

        speech_recognizer.recognized.connect(recognized_cb)
        speech_recognizer.session_stopped.connect(stop_cb)
        speech_recognizer.canceled.connect(canceled_cb)

        speech_recognizer.start_continuous_recognition()

        # Wait for completion
        import time

        while not done:
            time.sleep(0.5)

        speech_recognizer.stop_continuous_recognition()

        if cancellation_error:
            raise RuntimeError(cancellation_error)

        duration = segments[-1].end_time if segments else 0.0

        return TranscriptionResult(
            segments=segments,
            full_text=" ".join(full_text_parts),
            duration=duration,
            language=self.language,
            metadata={
                "diarization_enabled": False,
                "custom_terms_count": len(self.custom_terms),
                "language_candidates": self.language_candidates,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _transcribe_with_diarization(self, audio_file_path: str, audio_config, progress_callback=None) -> TranscriptionResult:
        """Transcription with speaker diarization."""
        # Create conversation transcriber
        conversation_transcriber = self.speechsdk.transcription.ConversationTranscriber(
            speech_config=self.speech_config, audio_config=audio_config
        )

        # Apply custom phrase list for improved recognition
        self._create_phrase_list(conversation_transcriber)

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
                    confidence=self._extract_confidence(result),
                )
                segments.append(segment)
                full_text_parts.append(result.text)
                logger.debug(f"Speaker {result.speaker_id}: {result.text}")
                if progress_callback:
                    try:
                        progress_callback(len(segments))
                    except Exception:
                        pass

        cancellation_error = None

        def stop_cb(evt):
            nonlocal done
            done = True
            logger.info("Diarized transcription session stopped")

        def canceled_cb(evt):
            nonlocal done, cancellation_error
            done = True
            cancellation = evt.result.cancellation_details
            logger.warning(f"Diarized transcription canceled: {cancellation.reason}")
            if cancellation.reason == self.speechsdk.CancellationReason.Error:
                cancellation_error = f"Speech service error: {cancellation.error_details}"
                logger.error(f"Cancellation error: {cancellation.error_details}")

        conversation_transcriber.transcribed.connect(transcribed_cb)
        conversation_transcriber.session_stopped.connect(stop_cb)
        conversation_transcriber.canceled.connect(canceled_cb)

        conversation_transcriber.start_transcribing_async().get()

        # Wait for completion
        import time

        while not done:
            time.sleep(0.5)

        conversation_transcriber.stop_transcribing_async().get()

        if cancellation_error:
            raise RuntimeError(cancellation_error)

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
                "custom_terms_count": len(self.custom_terms),
                "language_candidates": self.language_candidates,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    def _extract_confidence(self, result) -> float:
        """Extract confidence score from recognition result."""
        try:
            import json

            details = json.loads(result.json)
            nbest = details.get("NBest", [])
            if nbest:
                return nbest[0].get("Confidence", 0.0)
        except Exception as e:
            logger.debug(f"Could not extract confidence score from result: {e}")
        return 0.0

    def diarize_fast(self, audio_file_path: str, progress_callback=None) -> List[Dict[str, Any]]:
        """
        Fast diarization using Azure Speech REST API (faster-than-real-time).

        Uses the Speech-to-Text v3.2 fast transcription endpoint which
        processes audio much faster than real-time ConversationTranscriber.

        Returns a list of dicts with speaker_id, start_time, end_time, text
        that can be merged onto Whisper segments.
        """
        import httpx

        logger.info(f"Running fast diarization for: {audio_file_path}")

        # --- Obtain auth header ---
        if self.use_managed_identity:
            # AAD auth: get token and use directly as Bearer token.
            # NOTE: This requires a custom subdomain on the Speech resource.
            # Regional endpoints (e.g. swedencentral.api.cognitive.microsoft.com)
            # do NOT support AAD auth. Use the custom subdomain endpoint instead:
            # https://<custom-subdomain>.cognitiveservices.azure.com/
            aad_token = self._credential.get_token(
                "https://cognitiveservices.azure.com/.default"
            ).token
            headers = {"Authorization": f"Bearer {aad_token}"}
            logger.info("Using AAD Bearer token for Fast Transcription API")
        else:
            headers = {"Ocp-Apim-Subscription-Key": self.speech_key}

        # --- Build definition ---
        # Per API spec (TranscribeDiarizationProperties):
        #   enabled: boolean (REQUIRED to activate diarization)
        #   maxSpeakers: int (min 2, max 35)
        max_spk = max(2, min(self.max_speakers or 4, 35))
        definition = {
            "locales": [self.language],
            "profanityFilterMode": "None",
            "diarization": {
                "enabled": True,
                "maxSpeakers": max_spk,
            },
        }
        logger.info(f"Fast transcription definition: {json.dumps(definition)}")

        # When using managed identity (AAD auth), a custom subdomain endpoint
        # is REQUIRED. Regional endpoints don't support AAD auth.
        if self.speech_endpoint:
            # Custom subdomain endpoint, e.g. https://<name>.cognitiveservices.azure.com/
            base_url = self.speech_endpoint.rstrip("/")
        elif self.use_managed_identity and self.speech_resource_id:
            # Derive custom subdomain from resource ID (last segment)
            resource_name = self.speech_resource_id.rstrip("/").split("/")[-1]
            base_url = f"https://{resource_name}.cognitiveservices.azure.com"
            logger.info(f"Derived custom subdomain endpoint: {base_url}")
        else:
            # Regional endpoint (API-key auth only)
            base_url = f"https://{self.speech_region}.api.cognitive.microsoft.com"

        url = (
            f"{base_url}/"
            f"speechtotext/transcriptions:transcribe?api-version=2024-11-15"
        )
        logger.info(f"Fast Transcription API URL: {url}")

        if progress_callback:
            try:
                progress_callback(0)
            except Exception:
                pass

        # --- Send multipart request ---
        file_size = os.path.getsize(audio_file_path)
        logger.info(
            f"Sending {file_size / 1024 / 1024:.1f} MB to Fast Transcription API"
        )

        with open(audio_file_path, "rb") as af:
            files = {
                "audio": (
                    os.path.basename(audio_file_path),
                    af,
                    "application/octet-stream",
                ),
                "definition": (None, json.dumps(definition), "application/json"),
            }
            # httpx timeout: 10 min should cover most meeting recordings
            with httpx.Client(timeout=600.0) as client:
                response = client.post(url, headers=headers, files=files)

        if response.status_code != 200:
            logger.error(
                f"Fast transcription API error ({response.status_code}): "
                f"{response.text[:500]}"
            )
            raise RuntimeError(
                f"Fast transcription API error ({response.status_code}): "
                f"{response.text[:300]}"
            )

        result = response.json()

        # --- Diagnostic logging (WARNING level so always visible) ---
        logger.warning(
            f"Fast API response keys: {list(result.keys())}, "
            f"phrases count: {len(result.get('phrases', []))}"
        )
        sample_phrases = result.get("phrases", [])[:2]
        for i, sp in enumerate(sample_phrases):
            logger.warning(
                f"  phrase[{i}] keys={list(sp.keys())}, "
                f"speaker={sp.get('speaker', 'MISSING')}, "
                f"offsetMs={sp.get('offsetMilliseconds', 'MISSING')}, "
                f"durationMs={sp.get('durationMilliseconds', 'MISSING')}"
            )

        # --- Parse phrases into diarization segments ---
        # The Fast Transcription API returns:
        #   offsetMilliseconds (int), durationMilliseconds (int), speaker (int)
        diarization_segments: List[Dict[str, Any]] = []
        for phrase in result.get("phrases", []):
            speaker_num = phrase.get("speaker")
            if speaker_num is None:
                # No speaker info — diarization wasn't applied for this phrase
                continue
            speaker_id = f"Guest-{speaker_num}"

            # Times are in milliseconds → convert to seconds
            offset_ms = phrase.get("offsetMilliseconds", 0)
            duration_ms = phrase.get("durationMilliseconds", 0)
            start_time = offset_ms / 1000.0
            end_time = start_time + (duration_ms / 1000.0)

            diarization_segments.append(
                {
                    "speaker_id": speaker_id,
                    "start_time": start_time,
                    "end_time": end_time,
                    "text": phrase.get("text", ""),
                }
            )

            if progress_callback:
                try:
                    progress_callback(len(diarization_segments))
                except Exception:
                    pass

        speakers = set(
            s["speaker_id"] for s in diarization_segments if s.get("speaker_id")
        )
        logger.warning(
            f"Fast diarization complete: {len(diarization_segments)} segments, "
            f"{len(speakers)} speakers: {sorted(speakers)}"
        )
        if diarization_segments:
            first = diarization_segments[0]
            last = diarization_segments[-1]
            logger.warning(
                f"  Segment time range: {first['start_time']:.2f}s - "
                f"{last['end_time']:.2f}s (speakers: {first['speaker_id']} ... "
                f"{last['speaker_id']})"
            )
        return diarization_segments

    def diarize_only(self, audio_file_path: str, progress_callback=None) -> List[Dict[str, Any]]:
        """
        Run speaker diarization only (no transcription text used).
        Falls back to real-time ConversationTranscriber (slower).

        Returns a list of dicts with speaker_id, start_time, end_time
        that can be merged onto Whisper segments.
        """
        logger.info(f"Running diarization-only pass for: {audio_file_path}")

        audio_config = self.speechsdk.audio.AudioConfig(filename=audio_file_path)
        conversation_transcriber = self.speechsdk.transcription.ConversationTranscriber(
            speech_config=self.speech_config, audio_config=audio_config
        )

        diarization_segments: List[Dict[str, Any]] = []
        done = False
        cancellation_error = None

        def transcribed_cb(evt):
            if evt.result.reason == self.speechsdk.ResultReason.RecognizedSpeech:
                result = evt.result
                diarization_segments.append({
                    "speaker_id": result.speaker_id,
                    "start_time": result.offset / 10000000.0,
                    "end_time": (result.offset + result.duration) / 10000000.0,
                    "text": result.text,
                })
                if progress_callback:
                    try:
                        progress_callback(len(diarization_segments))
                    except Exception:
                        pass

        def stop_cb(evt):
            nonlocal done
            done = True

        def canceled_cb(evt):
            nonlocal done, cancellation_error
            done = True
            cancellation = evt.result.cancellation_details
            if cancellation.reason == self.speechsdk.CancellationReason.Error:
                cancellation_error = f"Speech service error: {cancellation.error_details}"
                logger.error(f"Diarization error: {cancellation.error_details}")

        conversation_transcriber.transcribed.connect(transcribed_cb)
        conversation_transcriber.session_stopped.connect(stop_cb)
        conversation_transcriber.canceled.connect(canceled_cb)

        conversation_transcriber.start_transcribing_async().get()

        import time
        while not done:
            time.sleep(0.5)

        conversation_transcriber.stop_transcribing_async().get()

        if cancellation_error:
            raise RuntimeError(cancellation_error)

        speakers = set(s["speaker_id"] for s in diarization_segments if s.get("speaker_id"))
        logger.info(f"Diarization complete: {len(diarization_segments)} segments, {len(speakers)} speakers")
        return diarization_segments

    def transcribe_realtime(self, audio_stream):
        """
        Transcribe audio in real-time from a stream.

        This is a placeholder for real-time transcription functionality.
        """
        raise NotImplementedError("Real-time transcription not yet implemented")
