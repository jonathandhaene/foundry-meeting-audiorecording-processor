"""
Unit tests for MeetingProcessor parallel batch processing.
"""

import os
import pytest
from unittest.mock import Mock, patch, call

from meeting_processor.pipeline import MeetingProcessor


@pytest.fixture
def mock_env():
    """Minimal env vars so ConfigManager doesn't raise."""
    env_vars = {
        "AZURE_SPEECH_KEY": "test_key",
        "AZURE_SPEECH_REGION": "eastus",
        "AZURE_TEXT_ANALYTICS_KEY": "test_analytics_key",
        "AZURE_TEXT_ANALYTICS_ENDPOINT": "https://test.endpoint.com",
    }
    with patch.dict(os.environ, env_vars):
        yield


@pytest.fixture
@patch("meeting_processor.pipeline.AzureSpeechTranscriber")
@patch("meeting_processor.pipeline.ContentAnalyzer")
@patch("meeting_processor.pipeline.AudioPreprocessor")
def processor(mock_preprocessor, mock_analyzer, mock_transcriber, mock_env):
    return MeetingProcessor()


class TestProcessBatchSequential:
    """Test sequential (default) batch processing behaviour."""

    @patch("meeting_processor.pipeline.AzureSpeechTranscriber")
    @patch("meeting_processor.pipeline.ContentAnalyzer")
    @patch("meeting_processor.pipeline.AudioPreprocessor")
    def test_sequential_batch_calls_process_audio_in_order(
        self, mock_preprocessor, mock_analyzer, mock_transcriber, mock_env, tmp_path
    ):
        """process_batch without parallel flag processes files sequentially."""
        proc = MeetingProcessor()

        call_order = []

        def fake_process(audio_file, output_dir, skip_preprocessing):
            call_order.append(audio_file)
            return {"input_file": audio_file, "output_directory": output_dir}

        proc.process_audio_file = fake_process

        files = ["a.wav", "b.wav", "c.wav"]
        results = proc.process_batch(files, str(tmp_path))

        assert call_order == files
        assert len(results) == 3
        assert all("input_file" in r for r in results)

    @patch("meeting_processor.pipeline.AzureSpeechTranscriber")
    @patch("meeting_processor.pipeline.ContentAnalyzer")
    @patch("meeting_processor.pipeline.AudioPreprocessor")
    def test_sequential_batch_captures_errors(
        self, mock_preprocessor, mock_analyzer, mock_transcriber, mock_env, tmp_path
    ):
        """Errors in individual files are captured, not raised."""
        proc = MeetingProcessor()

        def fake_process(audio_file, output_dir, skip_preprocessing):
            if audio_file == "bad.wav":
                raise RuntimeError("Bad file")
            return {"input_file": audio_file}

        proc.process_audio_file = fake_process

        results = proc.process_batch(["good.wav", "bad.wav"], str(tmp_path))

        assert len(results) == 2
        assert "input_file" in results[0]
        assert results[1]["error"] == "Bad file"


class TestProcessBatchParallel:
    """Test parallel batch processing behaviour."""

    @patch("meeting_processor.pipeline.AzureSpeechTranscriber")
    @patch("meeting_processor.pipeline.ContentAnalyzer")
    @patch("meeting_processor.pipeline.AudioPreprocessor")
    def test_parallel_batch_returns_all_results(
        self, mock_preprocessor, mock_analyzer, mock_transcriber, mock_env, tmp_path
    ):
        """Parallel batch produces one result per input file."""
        proc = MeetingProcessor()

        def fake_process(audio_file, output_dir, skip_preprocessing):
            return {"input_file": audio_file, "output_directory": output_dir}

        proc.process_audio_file = fake_process

        files = ["x.wav", "y.wav", "z.wav"]
        results = proc.process_batch(files, str(tmp_path), parallel=True, max_concurrent=3)

        assert len(results) == 3
        result_files = {r["input_file"] for r in results}
        assert result_files == set(files)

    @patch("meeting_processor.pipeline.AzureSpeechTranscriber")
    @patch("meeting_processor.pipeline.ContentAnalyzer")
    @patch("meeting_processor.pipeline.AudioPreprocessor")
    def test_parallel_batch_captures_errors(
        self, mock_preprocessor, mock_analyzer, mock_transcriber, mock_env, tmp_path
    ):
        """Errors in parallel tasks are captured per-file."""
        proc = MeetingProcessor()

        def fake_process(audio_file, output_dir, skip_preprocessing):
            if "bad" in audio_file:
                raise ValueError("Simulated failure")
            return {"input_file": audio_file}

        proc.process_audio_file = fake_process

        files = ["ok1.wav", "bad.wav", "ok2.wav"]
        results = proc.process_batch(files, str(tmp_path), parallel=True, max_concurrent=3)

        assert len(results) == 3
        errors = [r for r in results if "error" in r]
        successes = [r for r in results if "input_file" in r and "error" not in r]
        assert len(errors) == 1
        assert len(successes) == 2
        assert errors[0]["error"] == "Simulated failure"

    @patch("meeting_processor.pipeline.AzureSpeechTranscriber")
    @patch("meeting_processor.pipeline.ContentAnalyzer")
    @patch("meeting_processor.pipeline.AudioPreprocessor")
    def test_parallel_batch_with_max_concurrent_one_is_sequential(
        self, mock_preprocessor, mock_analyzer, mock_transcriber, mock_env, tmp_path
    ):
        """parallel=True with max_concurrent=1 still produces correct results."""
        proc = MeetingProcessor()

        def fake_process(audio_file, output_dir, skip_preprocessing):
            return {"input_file": audio_file}

        proc.process_audio_file = fake_process

        files = ["a.wav", "b.wav"]
        results = proc.process_batch(files, str(tmp_path), parallel=True, max_concurrent=1)

        assert len(results) == 2

    @patch("meeting_processor.pipeline.AzureSpeechTranscriber")
    @patch("meeting_processor.pipeline.ContentAnalyzer")
    @patch("meeting_processor.pipeline.AudioPreprocessor")
    def test_parallel_false_max_concurrent_ignored(
        self, mock_preprocessor, mock_analyzer, mock_transcriber, mock_env, tmp_path
    ):
        """When parallel=False, max_concurrent is ignored and sequential path runs."""
        proc = MeetingProcessor()

        def fake_process(audio_file, output_dir, skip_preprocessing):
            return {"input_file": audio_file}

        proc.process_audio_file = fake_process

        files = ["a.wav", "b.wav"]
        # parallel=False with high max_concurrent should still be sequential
        results = proc.process_batch(files, str(tmp_path), parallel=False, max_concurrent=10)

        assert len(results) == 2

    @patch("meeting_processor.pipeline.AzureSpeechTranscriber")
    @patch("meeting_processor.pipeline.ContentAnalyzer")
    @patch("meeting_processor.pipeline.AudioPreprocessor")
    def test_batch_creates_output_directory(
        self, mock_preprocessor, mock_analyzer, mock_transcriber, mock_env, tmp_path
    ):
        """process_batch creates the output directory if it doesn't exist."""
        proc = MeetingProcessor()
        proc.process_audio_file = Mock(return_value={"input_file": "a.wav"})

        output = tmp_path / "nested" / "output"
        assert not output.exists()

        proc.process_batch(["a.wav"], str(output))

        assert output.exists()
