"""
Whisper transcription module using OpenAI's Whisper model.

This module provides an alternative transcription method using
OpenAI's Whisper for local or API-based transcription.
Supports Azure OpenAI Whisper via managed identity.
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

try:
    from azure.identity import DefaultAzureCredential
except ImportError:
    DefaultAzureCredential = None  # type: ignore

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """
    Handles speech transcription using OpenAI's Whisper.

    Supports:
    - Local model inference
    - OpenAI API integration
    - Azure OpenAI Whisper (managed identity)
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
        azure_openai_endpoint: Optional[str] = None,
        azure_openai_deployment: Optional[str] = None,
        use_managed_identity: bool = False,
        temperature: Optional[float] = None,
        initial_prompt: Optional[str] = None,
    ):
        """
        Initialize Whisper transcriber.

        Args:
            model_size: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
            language: Language code (None for auto-detection)
            use_api: Use OpenAI API instead of local model
            api_key: OpenAI API key (required if use_api=True and not using Azure)
            custom_terms: List of custom terminology for improved recognition
            azure_openai_endpoint: Azure OpenAI endpoint URL
            azure_openai_deployment: Azure OpenAI Whisper deployment name
            use_managed_identity: Use Azure AD managed identity for Azure OpenAI
            temperature: Sampling temperature (0.0-1.0) for transcription
            initial_prompt: Optional text to guide the transcription style
        """
        self.model_size = model_size
        self.language = language
        self.use_api = use_api
        self.api_key = api_key
        self.custom_terms = custom_terms or []
        self.azure_openai_endpoint = azure_openai_endpoint
        self.azure_openai_deployment = azure_openai_deployment
        self.use_managed_identity = use_managed_identity
        self.temperature = temperature
        self.initial_prompt = initial_prompt

        # Azure OpenAI Whisper via managed identity
        if azure_openai_endpoint and azure_openai_deployment:
            if openai is None:
                raise ImportError("OpenAI package not available. Install with: pip install openai")
            if use_managed_identity:
                if DefaultAzureCredential is None:
                    raise ImportError("azure-identity package is required for managed identity auth")
                credential = DefaultAzureCredential()
                from azure.identity import get_bearer_token_provider
                token_provider = get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")
                self.client = openai.AzureOpenAI(
                    azure_endpoint=azure_openai_endpoint,
                    azure_ad_token_provider=token_provider,
                    api_version="2024-06-01",
                )
            else:
                self.client = openai.AzureOpenAI(
                    azure_endpoint=azure_openai_endpoint,
                    api_key=api_key,
                    api_version="2024-06-01",
                )
            self.use_azure_openai = True
            logger.info(f"Using Azure OpenAI Whisper: {azure_openai_endpoint} / {azure_openai_deployment}")
        elif use_api:
            if not api_key:
                raise ValueError("API key required when use_api=True")
            if openai is None:
                raise ImportError("OpenAI package not available. Install with: pip install openai")
            self.client = openai.OpenAI(api_key=api_key)
            self.use_azure_openai = False
        else:
            if whisper is None:
                raise ImportError("Whisper package not available. Install with: pip install openai-whisper")
            self.whisper = whisper
            self.use_azure_openai = False
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
        """Transcribe using OpenAI or Azure OpenAI Whisper API."""
        if self.use_azure_openai:
            logger.info(f"Using Azure OpenAI Whisper (deployment: {self.azure_openai_deployment})")
        else:
            logger.info("Using OpenAI Whisper API")

        # Generate initial prompt with custom terms (user prompt takes precedence)
        if self.initial_prompt:
            initial_prompt = self.initial_prompt
        else:
            initial_prompt = self._generate_initial_prompt()

        with open(audio_file_path, "rb") as audio_file:
            # Build API parameters
            api_params = {
                "model": self.azure_openai_deployment if self.use_azure_openai else "whisper-1",
                "file": audio_file,
                "response_format": "verbose_json",
            }

            if self.language:
                api_params["language"] = self.language

            if initial_prompt:
                api_params["prompt"] = initial_prompt

            if self.temperature is not None:
                api_params["temperature"] = self.temperature

            response = self.client.audio.transcriptions.create(**api_params)

        segments = []
        full_text_parts = []

        # Process API response segments
        response_segments = getattr(response, "segments", None) or []
        for segment_data in response_segments:
            # Handle both dict and object responses
            if isinstance(segment_data, dict):
                text = segment_data.get("text", "").strip()
                start = segment_data.get("start", 0.0)
                end = segment_data.get("end", 0.0)
                lang = segment_data.get("language")
            else:
                text = getattr(segment_data, "text", "").strip()
                start = getattr(segment_data, "start", 0.0)
                end = getattr(segment_data, "end", 0.0)
                lang = getattr(segment_data, "language", None)

            segment = TranscriptionSegment(
                text=text,
                start_time=start,
                end_time=end,
                speaker_id=None,
                language=lang or getattr(response, "language", None),
                confidence=0.0,
            )
            segments.append(segment)
            full_text_parts.append(text)

        duration = getattr(response, "duration", 0.0) or 0.0

        method_label = "azure_openai_whisper" if self.use_azure_openai else "whisper_api"

        return TranscriptionResult(
            segments=segments,
            full_text=getattr(response, "text", " ".join(full_text_parts)),
            duration=duration,
            language=getattr(response, "language", self.language or "auto"),
            metadata={
                "model": self.azure_openai_deployment if self.use_azure_openai else "whisper-1",
                "method": method_label,
                "diarization_enabled": False,
                "custom_terms_count": len(self.custom_terms),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

    @staticmethod
    def merge_diarization(
        whisper_result: TranscriptionResult,
        diarization_segments: List[Dict[str, Any]],
    ) -> TranscriptionResult:
        """
        Merge speaker IDs from Azure Speech diarization onto Whisper segments.

        For each Whisper segment, find the diarization segment with maximum
        temporal overlap and assign its speaker_id.
        """
        if not diarization_segments:
            return whisper_result

        # Diagnostic: log time ranges for debugging overlap issues
        ws_segs = whisper_result.segments
        if ws_segs:
            logger.warning(
                f"Merge: Whisper time range: {ws_segs[0].start_time:.2f}s - "
                f"{ws_segs[-1].end_time:.2f}s ({len(ws_segs)} segments)"
            )
        if diarization_segments:
            ds_starts = [d["start_time"] for d in diarization_segments]
            ds_ends = [d["end_time"] for d in diarization_segments]
            logger.warning(
                f"Merge: Diarization time range: {min(ds_starts):.2f}s - "
                f"{max(ds_ends):.2f}s ({len(diarization_segments)} segments)"
            )

        def _overlap(ws_start, ws_end, ds_start, ds_end):
            """Return overlap duration between two intervals."""
            start = max(ws_start, ds_start)
            end = min(ws_end, ds_end)
            return max(0.0, end - start)

        updated_segments: List[TranscriptionSegment] = []
        speakers_found: set = set()

        for seg in whisper_result.segments:
            best_speaker = None
            best_overlap = 0.0

            for ds in diarization_segments:
                ov = _overlap(
                    seg.start_time, seg.end_time,
                    ds["start_time"], ds["end_time"],
                )
                if ov > best_overlap:
                    best_overlap = ov
                    best_speaker = ds.get("speaker_id")

            new_seg = TranscriptionSegment(
                text=seg.text,
                start_time=seg.start_time,
                end_time=seg.end_time,
                speaker_id=best_speaker,
                language=seg.language,
                confidence=seg.confidence,
            )
            updated_segments.append(new_seg)
            if best_speaker:
                speakers_found.add(best_speaker)

        metadata = dict(whisper_result.metadata)
        metadata["diarization_enabled"] = True
        metadata["speaker_count"] = len(speakers_found)
        metadata["speakers"] = sorted(speakers_found)
        metadata["diarization_method"] = "hybrid_azure_speech"

        logger.warning(
            f"Merge result: {len(speakers_found)} speakers assigned "
            f"({sorted(speakers_found)})"
        )

        return TranscriptionResult(
            segments=updated_segments,
            full_text=whisper_result.full_text,
            duration=whisper_result.duration,
            language=whisper_result.language,
            metadata=metadata,
        )

    def _calculate_confidence(self, segment_data: Dict[str, Any]) -> float:
        """Calculate average confidence from word-level data."""
        words = segment_data.get("words", [])
        if not words:
            return 0.0

        # Average probability of all words in segment
        probabilities = [word.get("probability", 0.0) for word in words]
        return sum(probabilities) / len(probabilities) if probabilities else 0.0
