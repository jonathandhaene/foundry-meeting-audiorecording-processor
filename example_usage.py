#!/usr/bin/env python
"""
Example usage script for the Meeting Audio Recording Processor.

This script demonstrates how to use the processor to analyze meeting audio files.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from meeting_processor.pipeline import MeetingProcessor
from meeting_processor.utils import ConfigManager, setup_logging


def main():
    """Run example processing."""
    # Setup logging
    setup_logging(level="INFO")
    
    print("=" * 70)
    print("Meeting Audio Recording Processor - Example Usage")
    print("=" * 70)
    print()
    
    # Check configuration
    print("Checking configuration...")
    config = ConfigManager()
    
    if not config.validate_config():
        print("\n❌ Configuration validation failed!")
        print("\nPlease ensure the following environment variables are set:")
        print("  - AZURE_SPEECH_KEY")
        print("  - AZURE_SPEECH_REGION")
        print("  - AZURE_TEXT_ANALYTICS_KEY")
        print("  - AZURE_TEXT_ANALYTICS_ENDPOINT")
        print("\nYou can set these in a .env file (see .env.example)")
        return 1
    
    print("✓ Configuration is valid")
    print()
    
    # Get Azure config
    azure_config = config.get_azure_config()
    processing_config = config.get_processing_config()
    
    print("Configuration:")
    print(f"  - Speech Region: {azure_config.speech_region}")
    print(f"  - Default Language: {processing_config.default_language}")
    print(f"  - Speaker Diarization: {'Enabled' if processing_config.enable_diarization else 'Disabled'}")
    print(f"  - Max Speakers: {processing_config.max_speakers}")
    print()
    
    # Initialize processor
    print("Initializing processor...")
    try:
        processor = MeetingProcessor(config)
        print("✓ Processor initialized successfully")
    except Exception as e:
        print(f"❌ Failed to initialize processor: {e}")
        return 1
    
    print()
    print("=" * 70)
    print("Example Usage:")
    print("=" * 70)
    print()
    
    print("1. Process a single audio file:")
    print()
    print("   python -m meeting_processor.pipeline audio_file.wav")
    print()
    
    print("2. Process with custom output directory:")
    print()
    print("   python -m meeting_processor.pipeline audio_file.wav --output ./output")
    print()
    
    print("3. Use in Python code:")
    print()
    print("   from meeting_processor.pipeline import MeetingProcessor")
    print("   ")
    print("   processor = MeetingProcessor()")
    print("   results = processor.process_audio_file('meeting.wav')")
    print("   print(results['transcription']['full_text'])")
    print()
    
    print("4. Batch processing:")
    print()
    print("   files = ['meeting1.wav', 'meeting2.wav']")
    print("   results = processor.process_batch(files, './batch_output')")
    print()
    
    print("=" * 70)
    print("Ready to process audio files!")
    print("=" * 70)
    print()
    
    # Check if sample audio file provided
    if len(sys.argv) > 1:
        audio_file = sys.argv[1]
        if os.path.exists(audio_file):
            print(f"\nProcessing sample file: {audio_file}")
            print("This may take a few minutes depending on file size...")
            print()
            
            try:
                results = processor.process_audio_file(audio_file)
                
                print("\n✓ Processing completed successfully!")
                print(f"\nResults saved to: {results.get('results_file', 'N/A')}")
                print(f"Transcription: {results.get('transcription_file', 'N/A')}")
                print(f"Summary: {results.get('summary_file', 'N/A')}")
                
                # Show preview
                if "transcription" in results:
                    trans = results["transcription"]
                    print(f"\nTranscription preview:")
                    print(f"  Duration: {trans.get('duration', 0):.1f} seconds")
                    full_text = trans.get('full_text', '')
                    preview = full_text[:200] + "..." if len(full_text) > 200 else full_text
                    print(f"  Text: {preview}")
                
                if "summary" in results:
                    summary = results["summary"]
                    topics = summary.get('topics', [])
                    if topics:
                        print(f"\n  Topics: {', '.join(topics[:5])}")
                
            except Exception as e:
                print(f"\n❌ Processing failed: {e}")
                import traceback
                traceback.print_exc()
                return 1
        else:
            print(f"\n❌ File not found: {audio_file}")
            return 1
    else:
        print("Tip: Run with an audio file to test processing:")
        print(f"  python {sys.argv[0]} your_audio_file.wav")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
