"""Unit tests for audio preprocessing module."""

import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import subprocess

from meeting_processor.audio import AudioPreprocessor


@pytest.fixture
def preprocessor():
    """Create an AudioPreprocessor instance."""
    return AudioPreprocessor(sample_rate=16000, channels=1)


@pytest.fixture
def temp_audio_file():
    """Create a temporary audio file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        # Write minimal WAV header
        f.write(b"RIFF")
        f.write((36).to_bytes(4, 'little'))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write((16).to_bytes(4, 'little'))
        f.write((1).to_bytes(2, 'little'))  # Audio format
        f.write((1).to_bytes(2, 'little'))  # Channels
        f.write((16000).to_bytes(4, 'little'))  # Sample rate
        f.write((32000).to_bytes(4, 'little'))  # Byte rate
        f.write((2).to_bytes(2, 'little'))  # Block align
        f.write((16).to_bytes(2, 'little'))  # Bits per sample
        f.write(b"data")
        f.write((0).to_bytes(4, 'little'))  # Data size
        temp_path = f.name
    
    yield temp_path
    
    # Cleanup
    if os.path.exists(temp_path):
        os.unlink(temp_path)


class TestAudioPreprocessor:
    """Test suite for AudioPreprocessor class."""

    def test_initialization(self):
        """Test preprocessor initialization."""
        preprocessor = AudioPreprocessor(
            sample_rate=16000,
            channels=1,
            bit_rate="16k"
        )
        assert preprocessor.sample_rate == 16000
        assert preprocessor.channels == 1
        assert preprocessor.bit_rate == "16k"

    def test_initialization_defaults(self):
        """Test preprocessor initialization with defaults."""
        preprocessor = AudioPreprocessor()
        assert preprocessor.sample_rate == 16000
        assert preprocessor.channels == 1
        assert preprocessor.bit_rate == "16k"

    @patch('subprocess.run')
    def test_normalize_audio_success(self, mock_run, preprocessor, temp_audio_file):
        """Test successful audio normalization."""
        mock_run.return_value = Mock(
            returncode=0,
            stderr="",
            stdout=""
        )
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "output.wav")
            
            # Mock the output file creation
            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = True
                
                result = preprocessor.normalize_audio(
                    temp_audio_file,
                    output_path=output_path,
                    apply_noise_reduction=True
                )
                
                assert result == output_path
                assert mock_run.called

    def test_normalize_audio_file_not_found(self, preprocessor):
        """Test normalization with non-existent file."""
        with pytest.raises(FileNotFoundError):
            preprocessor.normalize_audio("nonexistent.wav")

    @patch('subprocess.run')
    def test_normalize_audio_ffmpeg_error(self, mock_run, preprocessor, temp_audio_file):
        """Test normalization when FFmpeg fails."""
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "ffmpeg", stderr="Error message"
        )
        
        with pytest.raises(RuntimeError):
            preprocessor.normalize_audio(temp_audio_file)

    @patch('subprocess.run')
    def test_convert_to_wav(self, mock_run, preprocessor, temp_audio_file):
        """Test audio conversion to WAV."""
        mock_run.return_value = Mock(returncode=0)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = os.path.join(temp_dir, "output.wav")
            
            with patch('pathlib.Path.exists') as mock_exists:
                mock_exists.return_value = True
                
                result = preprocessor.convert_to_wav(
                    temp_audio_file,
                    output_path=output_path
                )
                
                assert result == output_path

    @patch('subprocess.run')
    def test_get_audio_info(self, mock_run, preprocessor, temp_audio_file):
        """Test getting audio file information."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout='{"format": {"duration": "10.5", "bit_rate": "128000", "size": "160000"}, "streams": [{"codec_type": "audio", "sample_rate": "44100", "channels": 2, "codec_name": "pcm_s16le"}]}'
        )
        
        info = preprocessor.get_audio_info(temp_audio_file)
        
        assert info["duration"] == 10.5
        assert info["sample_rate"] == 44100
        assert info["channels"] == 2
        assert info["codec"] == "pcm_s16le"

    @patch('subprocess.run')
    def test_get_audio_info_error(self, mock_run, preprocessor, temp_audio_file):
        """Test getting audio info when ffprobe fails."""
        mock_run.side_effect = subprocess.CalledProcessError(1, "ffprobe")
        
        info = preprocessor.get_audio_info(temp_audio_file)
        
        assert info == {}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
