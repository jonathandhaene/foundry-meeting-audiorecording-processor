"""
Main processing pipeline for meeting audio recordings.

This module orchestrates the complete workflow from audio preprocessing
through transcription to content analysis.
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Any, Optional
import json

from meeting_processor.audio import AudioPreprocessor
from meeting_processor.transcription import AzureSpeechTranscriber, TranscriptionResult
from meeting_processor.nlp import ContentAnalyzer, MeetingSummary
from meeting_processor.utils import ConfigManager, setup_logging

logger = logging.getLogger(__name__)


class MeetingProcessor:
    """
    Main pipeline for processing meeting audio recordings.

    Handles:
    1. Audio preprocessing and normalization
    2. Speech-to-text transcription with diarization
    3. Content understanding and insight extraction
    """

    def __init__(self, config_manager: Optional[ConfigManager] = None):
        """
        Initialize the meeting processor.

        Args:
            config_manager: Configuration manager instance (creates default if None)
        """
        if config_manager is None:
            config_manager = ConfigManager()

        self.config_manager = config_manager
        self.azure_config = config_manager.get_azure_config()
        self.processing_config = config_manager.get_processing_config()

        # Initialize components
        self.audio_preprocessor = AudioPreprocessor(
            sample_rate=self.processing_config.sample_rate, channels=self.processing_config.channels
        )

        self.transcriber = AzureSpeechTranscriber(
            speech_key=self.azure_config.speech_key,
            speech_region=self.azure_config.speech_region,
            language=self.processing_config.default_language,
            enable_diarization=self.processing_config.enable_diarization,
            max_speakers=self.processing_config.max_speakers,
        )

        self.content_analyzer = ContentAnalyzer(
            text_analytics_key=self.azure_config.text_analytics_key,
            text_analytics_endpoint=self.azure_config.text_analytics_endpoint,
            language=self.processing_config.default_language.split("-")[0],  # Extract language code
        )

        logger.info("Meeting processor initialized successfully")

    def process_audio_file(
        self, audio_file_path: str, output_dir: Optional[str] = None, skip_preprocessing: bool = False
    ) -> Dict[str, Any]:
        """
        Process a meeting audio file end-to-end.

        Args:
            audio_file_path: Path to the audio file to process
            output_dir: Directory to save output files (default: same as input)
            skip_preprocessing: Skip audio preprocessing if True

        Returns:
            Dictionary containing all processing results
        """
        logger.info(f"Starting processing for: {audio_file_path}")

        audio_path = Path(audio_file_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_file_path}")

        if output_dir is None:
            output_dir = audio_path.parent
        else:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        results = {"input_file": str(audio_path), "output_directory": str(output_dir)}

        # Step 1: Audio Preprocessing
        if not skip_preprocessing:
            logger.info("Step 1/3: Preprocessing audio...")
            preprocessed_path = self.preprocess_audio(str(audio_path), output_dir=str(output_dir))
            results["preprocessed_audio"] = preprocessed_path
            audio_for_transcription = preprocessed_path
        else:
            logger.info("Skipping audio preprocessing")
            audio_for_transcription = str(audio_path)

        # Step 2: Transcription
        logger.info("Step 2/3: Transcribing audio...")
        transcription = self.transcribe_audio(audio_for_transcription)
        results["transcription"] = transcription.to_dict()

        # Save transcription
        transcription_file = output_dir / f"{audio_path.stem}_transcription.json"
        with open(transcription_file, "w", encoding="utf-8") as f:
            json.dump(results["transcription"], f, indent=2, ensure_ascii=False)
        results["transcription_file"] = str(transcription_file)
        logger.info(f"Transcription saved to: {transcription_file}")

        # Step 3: Content Analysis
        logger.info("Step 3/3: Analyzing content...")
        summary = self.analyze_content(transcription.full_text)
        results["summary"] = summary.to_dict()

        # Save summary
        summary_file = output_dir / f"{audio_path.stem}_summary.json"
        with open(summary_file, "w", encoding="utf-8") as f:
            json.dump(results["summary"], f, indent=2, ensure_ascii=False)
        results["summary_file"] = str(summary_file)
        logger.info(f"Summary saved to: {summary_file}")

        # Save complete results
        results_file = output_dir / f"{audio_path.stem}_results.json"
        with open(results_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        results["results_file"] = str(results_file)

        logger.info(f"Processing complete! Results saved to: {results_file}")
        return results

    def preprocess_audio(self, audio_file_path: str, output_dir: Optional[str] = None) -> str:
        """
        Preprocess audio file for transcription.

        Args:
            audio_file_path: Path to input audio file
            output_dir: Directory for output file

        Returns:
            Path to preprocessed audio file
        """
        audio_path = Path(audio_file_path)

        if output_dir:
            output_path = Path(output_dir) / f"{audio_path.stem}_normalized.wav"
        else:
            output_path = None

        # Get audio info
        audio_info = self.audio_preprocessor.get_audio_info(str(audio_path))
        logger.info(f"Input audio info: {audio_info}")

        # Normalize audio
        normalized_path = self.audio_preprocessor.normalize_audio(
            input_path=str(audio_path),
            output_path=str(output_path) if output_path else None,
            apply_noise_reduction=self.processing_config.apply_noise_reduction,
        )

        return normalized_path

    def transcribe_audio(self, audio_file_path: str) -> TranscriptionResult:
        """
        Transcribe audio file to text.

        Args:
            audio_file_path: Path to audio file

        Returns:
            TranscriptionResult object
        """
        return self.transcriber.transcribe_audio(audio_file_path)

    def analyze_content(self, transcription_text: str) -> MeetingSummary:
        """
        Analyze transcription content for insights.

        Args:
            transcription_text: Transcribed text to analyze

        Returns:
            MeetingSummary object
        """
        return self.content_analyzer.analyze_transcription(transcription_text)

    def process_batch(
        self,
        audio_files: list[str],
        output_dir: str,
        skip_preprocessing: bool = False,
        max_concurrent: int = 1,
        parallel: bool = False,
    ) -> list[Dict[str, Any]]:
        """
        Process multiple audio files in batch.

        Args:
            audio_files: List of audio file paths
            output_dir: Directory to save all outputs
            skip_preprocessing: Skip audio preprocessing if True
            max_concurrent: Maximum number of files to process concurrently (used when parallel=True)
            parallel: Enable parallel processing using a thread pool

        Returns:
            List of result dictionaries, one per file
        """
        logger.info(
            f"Starting batch processing of {len(audio_files)} files (parallel={parallel}, max_concurrent={max_concurrent})"
        )

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        if parallel:
            return self._process_batch_parallel(audio_files, output_path, skip_preprocessing, max(1, max_concurrent))

        results = []
        for i, audio_file in enumerate(audio_files, 1):
            logger.info(f"Processing file {i}/{len(audio_files)}: {audio_file}")
            try:
                result = self.process_audio_file(
                    audio_file, output_dir=str(output_path), skip_preprocessing=skip_preprocessing
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {audio_file}: {e}")
                results.append({"input_file": audio_file, "error": str(e)})

        logger.info(f"Batch processing complete. Processed {len(results)} files")
        return results

    def _process_batch_parallel(
        self,
        audio_files: list[str],
        output_path: Path,
        skip_preprocessing: bool,
        max_concurrent: int,
    ) -> list[Dict[str, Any]]:
        """Process batch files in parallel using a thread pool."""
        results: list[Optional[Dict[str, Any]]] = [None] * len(audio_files)

        with ThreadPoolExecutor(max_workers=max_concurrent, thread_name_prefix="batch") as executor:
            future_to_index = {
                executor.submit(
                    self.process_audio_file,
                    audio_file,
                    str(output_path),
                    skip_preprocessing,
                ): i
                for i, audio_file in enumerate(audio_files)
            }

            for future in as_completed(future_to_index):
                idx = future_to_index[future]
                audio_file = audio_files[idx]
                try:
                    results[idx] = future.result()
                    logger.info(f"Parallel batch: completed {audio_file}")
                except Exception as e:
                    logger.error(f"Parallel batch: failed to process {audio_file}: {e}")
                    results[idx] = {"input_file": audio_file, "error": str(e)}

        logger.info(f"Parallel batch processing complete. Processed {len(results)} files")
        return results


def main():
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Process meeting audio recordings with Azure services")
    parser.add_argument("audio_file", help="Path to audio file to process")
    parser.add_argument("-o", "--output", help="Output directory (default: same as input file)", default=None)
    parser.add_argument("--skip-preprocessing", action="store_true", help="Skip audio preprocessing step")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], default="INFO", help="Logging level")
    parser.add_argument("--env-file", help="Path to .env file with configuration", default=None)

    args = parser.parse_args()

    # Setup logging
    setup_logging(level=args.log_level)

    # Initialize processor
    config_manager = ConfigManager(env_file=args.env_file)
    processor = MeetingProcessor(config_manager)

    # Process audio
    try:
        results = processor.process_audio_file(
            args.audio_file, output_dir=args.output, skip_preprocessing=args.skip_preprocessing
        )
        print("\n=== Processing Complete ===")
        print(f"Results saved to: {results['results_file']}")
        print(f"Transcription: {results['transcription_file']}")
        print(f"Summary: {results['summary_file']}")
    except Exception as e:
        logger.error(f"Processing failed: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
