"""
Audio preprocessing module for meeting recordings.

This module handles audio file normalization, format conversion,
and preparation for transcription services.
"""

import subprocess  # nosec B404 - Required for safe ffmpeg/ffprobe execution with validated inputs
import json
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class AudioPreprocessor:
    """
    Handles audio preprocessing tasks including normalization,
    format conversion, and noise reduction.
    """

    def __init__(self, sample_rate: int = 16000, channels: int = 1, bit_rate: str = "16k"):
        """
        Initialize the audio preprocessor.

        Args:
            sample_rate: Target sample rate in Hz (default: 16000)
            channels: Number of audio channels (default: 1 for mono)
            bit_rate: Target bit rate (default: "16k")
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.bit_rate = bit_rate
        self._check_ffmpeg()

    def _check_ffmpeg(self) -> None:
        """Check if FFmpeg is installed and available."""
        try:
            subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)  # nosec B603 B607 - Safe call to ffmpeg with no user input
        except (subprocess.CalledProcessError, FileNotFoundError):
            logger.warning(
                "FFmpeg not found. Audio preprocessing may not work properly. "
                "Please install FFmpeg: https://ffmpeg.org/download.html"
            )

    def normalize_audio(self, input_path: str, output_path: Optional[str] = None, apply_noise_reduction: bool = True) -> str:
        """
        Normalize audio file to standard format for transcription.

        Args:
            input_path: Path to input audio file
            output_path: Path for output file (default: same as input with _normalized suffix)
            apply_noise_reduction: Whether to apply noise reduction filter

        Returns:
            Path to the normalized audio file

        Raises:
            FileNotFoundError: If input file doesn't exist
            RuntimeError: If FFmpeg processing fails
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_normalized.wav"
        else:
            output_path = Path(output_path)

        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Build FFmpeg command
        cmd = [
            "ffmpeg",
            "-i",
            str(input_path),
            "-ar",
            str(self.sample_rate),
            "-ac",
            str(self.channels),
            "-b:a",
            self.bit_rate,
            "-y",  # Overwrite output file if exists
        ]

        # Add noise reduction filter if requested
        if apply_noise_reduction:
            cmd.extend(["-af", "highpass=f=200,lowpass=f=3000,afftdn=nf=-25"])

        cmd.append(str(output_path))

        logger.info(f"Normalizing audio: {input_path} -> {output_path}")

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)  # nosec B603 - ffmpeg command with validated file paths
            logger.debug(f"FFmpeg output: {result.stderr}")
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise RuntimeError(f"Failed to normalize audio: {e.stderr}")

        if not output_path.exists():
            raise RuntimeError(f"Output file was not created: {output_path}")

        logger.info(f"Audio normalized successfully: {output_path}")
        return str(output_path)

    def get_audio_info(self, audio_path: str) -> Dict[str, Any]:
        """
        Get information about an audio file.

        Args:
            audio_path: Path to audio file

        Returns:
            Dictionary with audio properties (duration, sample_rate, channels, etc.)
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(audio_path)]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)  # nosec B603 - ffprobe command with validated file path
            data = json.loads(result.stdout)

            # Extract audio stream info
            audio_stream = next((s for s in data.get("streams", []) if s.get("codec_type") == "audio"), {})

            return {
                "duration": float(data.get("format", {}).get("duration", 0)),
                "sample_rate": int(audio_stream.get("sample_rate", 0)),
                "channels": int(audio_stream.get("channels", 0)),
                "codec": audio_stream.get("codec_name", "unknown"),
                "bit_rate": int(data.get("format", {}).get("bit_rate", 0)),
                "size": int(data.get("format", {}).get("size", 0)),
            }
        except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to get audio info: {e}")
            return {}

    def convert_to_wav(self, input_path: str, output_path: Optional[str] = None) -> str:
        """
        Convert audio file to WAV format.

        Args:
            input_path: Path to input audio file
            output_path: Path for output WAV file

        Returns:
            Path to the converted WAV file
        """
        input_path = Path(input_path)
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")

        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}.wav"
        else:
            output_path = Path(output_path)

        if output_path.exists() and output_path == input_path:
            logger.info(f"File is already in WAV format: {input_path}")
            return str(output_path)

        cmd = ["ffmpeg", "-i", str(input_path), "-acodec", "pcm_s16le", "-y", str(output_path)]

        logger.info(f"Converting to WAV: {input_path} -> {output_path}")

        try:
            subprocess.run(cmd, capture_output=True, check=True)  # nosec B603 - ffmpeg command with validated file paths
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Failed to convert to WAV: {e.stderr}")

        logger.info(f"Converted to WAV successfully: {output_path}")
        return str(output_path)
