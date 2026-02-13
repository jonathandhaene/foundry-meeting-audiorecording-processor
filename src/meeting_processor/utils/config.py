"""Configuration management for the application."""

import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class AzureConfig:
    """Azure service configuration."""
    speech_key: str
    speech_region: str
    text_analytics_key: str
    text_analytics_endpoint: str
    storage_connection_string: Optional[str] = None
    storage_container_name: Optional[str] = None


@dataclass
class ProcessingConfig:
    """Audio processing configuration."""
    default_language: str = "en-US"
    enable_diarization: bool = True
    max_speakers: int = 10
    sample_rate: int = 16000
    channels: int = 1
    apply_noise_reduction: bool = True


class ConfigManager:
    """Manages application configuration from environment variables."""

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration manager.

        Args:
            env_file: Path to .env file (optional)
        """
        if env_file:
            load_dotenv(env_file)
        else:
            load_dotenv()

    def get_azure_config(self) -> AzureConfig:
        """Get Azure service configuration."""
        return AzureConfig(
            speech_key=self._get_required_env("AZURE_SPEECH_KEY"),
            speech_region=self._get_required_env("AZURE_SPEECH_REGION"),
            text_analytics_key=self._get_required_env("AZURE_TEXT_ANALYTICS_KEY"),
            text_analytics_endpoint=self._get_required_env("AZURE_TEXT_ANALYTICS_ENDPOINT"),
            storage_connection_string=os.getenv("AZURE_STORAGE_CONNECTION_STRING"),
            storage_container_name=os.getenv("AZURE_STORAGE_CONTAINER_NAME", "meeting-audio-files")
        )

    def get_processing_config(self) -> ProcessingConfig:
        """Get audio processing configuration."""
        return ProcessingConfig(
            default_language=os.getenv("DEFAULT_LANGUAGE", "en-US"),
            enable_diarization=os.getenv("ENABLE_SPEAKER_DIARIZATION", "true").lower() == "true",
            max_speakers=int(os.getenv("MAX_SPEAKERS", "10")),
            sample_rate=int(os.getenv("AUDIO_SAMPLE_RATE", "16000")),
            channels=int(os.getenv("AUDIO_CHANNELS", "1")),
            apply_noise_reduction=os.getenv("APPLY_NOISE_REDUCTION", "true").lower() == "true"
        )

    def _get_required_env(self, key: str) -> str:
        """Get required environment variable or raise error."""
        value = os.getenv(key)
        if not value:
            raise ValueError(
                f"Required environment variable '{key}' not set. "
                f"Please check your .env file or environment configuration."
            )
        return value

    def validate_config(self) -> bool:
        """
        Validate that all required configuration is present.

        Returns:
            True if configuration is valid, False otherwise
        """
        try:
            self.get_azure_config()
            self.get_processing_config()
            return True
        except ValueError as e:
            print(f"Configuration validation failed: {e}")
            return False
