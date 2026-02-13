"""Pytest configuration and shared fixtures."""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

# Mock Azure and Whisper modules at the module level for all tests
@pytest.fixture(scope="session", autouse=True)
def mock_external_modules():
    """Mock external modules that might not be installed."""
    # Mock whisper module
    if 'whisper' not in sys.modules:
        mock_whisper = Mock()
        mock_whisper.load_model = Mock(return_value=Mock())
        sys.modules['whisper'] = mock_whisper
    
    # Mock Azure Speech SDK
    if 'azure' not in sys.modules:
        sys.modules['azure'] = Mock()
    if 'azure.cognitiveservices' not in sys.modules:
        sys.modules['azure.cognitiveservices'] = Mock()
    if 'azure.cognitiveservices.speech' not in sys.modules:
        mock_speech = Mock()
        mock_speech.SpeechConfig = Mock()
        mock_speech.OutputFormat.Detailed = "Detailed"
        mock_speech.ResultReason.RecognizedSpeech = "RecognizedSpeech"
        mock_speech.audio.AudioConfig = Mock()
        sys.modules['azure.cognitiveservices.speech'] = mock_speech
    
    # Mock OpenAI module
    if 'openai' not in sys.modules:
        mock_openai = Mock()
        sys.modules['openai'] = mock_openai
    
    yield
