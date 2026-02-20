"""Unit tests for configuration management."""

import pytest
import os
from unittest.mock import patch

from meeting_processor.utils import ConfigManager, AzureConfig, ProcessingConfig


class TestConfigManager:
    """Test ConfigManager class."""

    def test_initialization(self):
        """Test config manager initialization."""
        manager = ConfigManager()
        assert manager is not None

    @patch.dict(
        os.environ,
        {
            "AZURE_SPEECH_KEY": "test_speech_key",
            "AZURE_SPEECH_REGION": "eastus",
            "AZURE_TEXT_ANALYTICS_KEY": "test_analytics_key",
            "AZURE_TEXT_ANALYTICS_ENDPOINT": "https://test.endpoint.com",
        },
    )
    def test_get_azure_config(self):
        """Test getting Azure configuration."""
        manager = ConfigManager()
        config = manager.get_azure_config()

        assert isinstance(config, AzureConfig)
        assert config.speech_key == "test_speech_key"
        assert config.speech_region == "eastus"
        assert config.text_analytics_key == "test_analytics_key"

    @patch.dict(os.environ, {"DEFAULT_LANGUAGE": "es-ES", "ENABLE_SPEAKER_DIARIZATION": "false", "MAX_SPEAKERS": "5"})
    def test_get_processing_config(self):
        """Test getting processing configuration."""
        manager = ConfigManager()
        config = manager.get_processing_config()

        assert isinstance(config, ProcessingConfig)
        assert config.default_language == "es-ES"
        assert config.enable_diarization is False
        assert config.max_speakers == 5

    def test_get_processing_config_defaults(self):
        """Test processing config with default values."""
        with patch.dict(os.environ, {}, clear=True):
            manager = ConfigManager()
            config = manager.get_processing_config()

            assert config.default_language == "en-US"
            assert config.enable_diarization is True
            assert config.max_speakers == 10

    def test_missing_required_config(self):
        """Test that missing Azure auth config results in None speech_key."""
        with patch.dict(os.environ, {}, clear=True):
            manager = ConfigManager()
            config = manager.get_azure_config()

            assert config.speech_key is None
            assert config.speech_resource_id is None

    @patch.dict(
        os.environ,
        {
            "AZURE_SPEECH_KEY": "test_key",
            "AZURE_SPEECH_REGION": "eastus",
            "AZURE_TEXT_ANALYTICS_KEY": "test_key",
            "AZURE_TEXT_ANALYTICS_ENDPOINT": "https://test.com",
        },
    )
    def test_validate_config_success(self):
        """Test successful configuration validation."""
        manager = ConfigManager()

        assert manager.validate_config() is True

    def test_validate_config_failure(self):
        """Test failed configuration validation."""
        with patch.dict(os.environ, {}, clear=True):
            manager = ConfigManager()

            assert manager.validate_config() is False


class TestDataClasses:
    """Test configuration dataclasses."""

    def test_azure_config_creation(self):
        """Test creating AzureConfig."""
        config = AzureConfig(
            speech_key="key1", speech_region="region1", text_analytics_key="key2", text_analytics_endpoint="endpoint1"
        )

        assert config.speech_key == "key1"
        assert config.speech_region == "region1"
        assert config.text_analytics_key == "key2"

    def test_processing_config_creation(self):
        """Test creating ProcessingConfig."""
        config = ProcessingConfig(default_language="fr-FR", enable_diarization=False, max_speakers=8)

        assert config.default_language == "fr-FR"
        assert config.enable_diarization is False
        assert config.max_speakers == 8


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
