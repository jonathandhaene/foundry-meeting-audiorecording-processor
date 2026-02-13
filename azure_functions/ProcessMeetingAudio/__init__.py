"""
Azure Function for processing meeting audio files.

This function is triggered by blob storage uploads and processes
the audio files through the meeting processor pipeline.
"""

import logging
import azure.functions as func
import json
import os
import tempfile
from pathlib import Path

# Import our meeting processor
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from meeting_processor.pipeline import MeetingProcessor
from meeting_processor.utils import ConfigManager, setup_logging


def main(myblob: func.InputStream, outputBlob: func.Out[str]) -> None:
    """
    Azure Function triggered by blob storage upload.
    
    Args:
        myblob: Input blob stream containing audio file
        outputBlob: Output blob for results
    """
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)
    
    logger.info(f"Processing blob: {myblob.name}, Size: {myblob.length} bytes")

    try:
        # Create temporary directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            # Save input blob to temp file
            input_file = temp_path / Path(myblob.name).name
            with open(input_file, 'wb') as f:
                f.write(myblob.read())
            
            logger.info(f"Saved input file to: {input_file}")

            # Initialize processor
            config_manager = ConfigManager()
            processor = MeetingProcessor(config_manager)

            # Process the audio file
            results = processor.process_audio_file(
                str(input_file),
                output_dir=str(temp_path)
            )

            # Write results to output blob
            output_data = json.dumps(results, indent=2)
            outputBlob.set(output_data)

            logger.info(f"Processing complete for: {myblob.name}")

    except Exception as e:
        logger.error(f"Error processing blob {myblob.name}: {e}", exc_info=True)
        error_result = {
            "error": str(e),
            "blob_name": myblob.name
        }
        outputBlob.set(json.dumps(error_result))
        raise
