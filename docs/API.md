# API Documentation

## Table of Contents

- [MeetingProcessor](#meetingprocessor)
- [AudioPreprocessor](#audiopreprocessor)
- [AzureSpeechTranscriber](#azurespeachtranscriber)
- [ContentAnalyzer](#contentanalyzer)
- [Data Models](#data-models)

## MeetingProcessor

Main pipeline class for processing meeting audio recordings.

### Constructor

```python
MeetingProcessor(config_manager: Optional[ConfigManager] = None)
```

**Parameters:**
- `config_manager`: Configuration manager instance (creates default if None)

**Example:**
```python
from meeting_processor.pipeline import MeetingProcessor
from meeting_processor.utils import ConfigManager

config = ConfigManager()
processor = MeetingProcessor(config)
```

### Methods

#### process_audio_file

```python
process_audio_file(
    audio_file_path: str,
    output_dir: Optional[str] = None,
    skip_preprocessing: bool = False
) -> Dict[str, Any]
```

Process a meeting audio file end-to-end.

**Parameters:**
- `audio_file_path`: Path to the audio file to process
- `output_dir`: Directory to save output files (default: same as input)
- `skip_preprocessing`: Skip audio preprocessing if True

**Returns:** Dictionary containing all processing results

**Example:**
```python
results = processor.process_audio_file(
    "meeting.wav",
    output_dir="./output"
)
print(results["transcription"]["full_text"])
```

#### process_batch

```python
process_batch(
    audio_files: list[str],
    output_dir: str,
    skip_preprocessing: bool = False
) -> list[Dict[str, Any]]
```

Process multiple audio files in batch.

**Parameters:**
- `audio_files`: List of audio file paths
- `output_dir`: Directory to save all outputs
- `skip_preprocessing`: Skip audio preprocessing if True

**Returns:** List of result dictionaries, one per file

**Example:**
```python
files = ["meeting1.wav", "meeting2.wav"]
results = processor.process_batch(files, "./batch_output")
```

---

## AudioPreprocessor

Handles audio preprocessing tasks including normalization and format conversion.

### Constructor

```python
AudioPreprocessor(
    sample_rate: int = 16000,
    channels: int = 1,
    bit_rate: str = "16k"
)
```

**Parameters:**
- `sample_rate`: Target sample rate in Hz (default: 16000)
- `channels`: Number of audio channels (default: 1 for mono)
- `bit_rate`: Target bit rate (default: "16k")

### Methods

#### normalize_audio

```python
normalize_audio(
    input_path: str,
    output_path: Optional[str] = None,
    apply_noise_reduction: bool = True
) -> str
```

Normalize audio file to standard format for transcription.

**Parameters:**
- `input_path`: Path to input audio file
- `output_path`: Path for output file
- `apply_noise_reduction`: Whether to apply noise reduction filter

**Returns:** Path to the normalized audio file

**Raises:**
- `FileNotFoundError`: If input file doesn't exist
- `RuntimeError`: If FFmpeg processing fails

#### get_audio_info

```python
get_audio_info(audio_path: str) -> Dict[str, Any]
```

Get information about an audio file.

**Returns:** Dictionary with audio properties:
```python
{
    "duration": 180.5,
    "sample_rate": 44100,
    "channels": 2,
    "codec": "pcm_s16le",
    "bit_rate": 128000,
    "size": 15728640
}
```

#### convert_to_wav

```python
convert_to_wav(
    input_path: str,
    output_path: Optional[str] = None
) -> str
```

Convert audio file to WAV format.

---

## AzureSpeechTranscriber

Handles speech transcription using Azure Speech Services.

### Constructor

```python
AzureSpeechTranscriber(
    speech_key: str,
    speech_region: str,
    language: str = "en-US",
    enable_diarization: bool = True,
    max_speakers: int = 10
)
```

**Parameters:**
- `speech_key`: Azure Speech Services API key
- `speech_region`: Azure region (e.g., 'eastus')
- `language`: Primary language code (e.g., 'en-US')
- `enable_diarization`: Enable speaker diarization
- `max_speakers`: Maximum number of speakers to identify

### Methods

#### transcribe_audio

```python
transcribe_audio(
    audio_file_path: str,
    languages: Optional[List[str]] = None
) -> TranscriptionResult
```

Transcribe audio file using Azure Speech Services.

**Parameters:**
- `audio_file_path`: Path to audio file
- `languages`: List of language codes for multi-language support

**Returns:** `TranscriptionResult` object

**Example:**
```python
transcriber = AzureSpeechTranscriber(
    speech_key="your_key",
    speech_region="eastus"
)

result = transcriber.transcribe_audio("meeting.wav")
print(f"Transcribed {len(result.segments)} segments")
print(f"Full text: {result.full_text}")
```

---

## ContentAnalyzer

Analyzes transcribed content using Azure Text Analytics.

### Constructor

```python
ContentAnalyzer(
    text_analytics_key: str,
    text_analytics_endpoint: str,
    language: str = "en"
)
```

**Parameters:**
- `text_analytics_key`: Azure Text Analytics API key
- `text_analytics_endpoint`: Azure Text Analytics endpoint URL
- `language`: Language code (e.g., 'en', 'es', 'fr')

### Methods

#### analyze_transcription

```python
analyze_transcription(
    transcription_text: str,
    extract_action_items: bool = True
) -> MeetingSummary
```

Analyze transcription text to extract insights.

**Parameters:**
- `transcription_text`: Full text of the transcription
- `extract_action_items`: Whether to extract action items

**Returns:** `MeetingSummary` object

**Example:**
```python
analyzer = ContentAnalyzer(
    text_analytics_key="your_key",
    text_analytics_endpoint="https://your-endpoint.com"
)

summary = analyzer.analyze_transcription(transcription_text)
print(f"Key topics: {summary.topics}")
print(f"Sentiment: {summary.sentiment['overall']}")
```

#### categorize_content

```python
categorize_content(
    text: str,
    categories: List[str]
) -> Dict[str, float]
```

Categorize content into predefined categories.

**Parameters:**
- `text`: Text to categorize
- `categories`: List of category names

**Returns:** Dictionary mapping categories to confidence scores

---

## Data Models

### TranscriptionSegment

Represents a single segment of transcribed text.

```python
@dataclass
class TranscriptionSegment:
    text: str
    start_time: float
    end_time: float
    speaker_id: Optional[str] = None
    language: Optional[str] = None
    confidence: float = 0.0
```

### TranscriptionResult

Complete transcription result with metadata.

```python
@dataclass
class TranscriptionResult:
    segments: List[TranscriptionSegment]
    full_text: str
    duration: float
    language: str
    metadata: Dict[str, Any]
```

### KeyPhrase

Represents an extracted key phrase.

```python
@dataclass
class KeyPhrase:
    text: str
    score: float
```

### ActionItem

Represents an identified action item.

```python
@dataclass
class ActionItem:
    text: str
    assignee: Optional[str] = None
    due_date: Optional[str] = None
```

### MeetingSummary

Summary of meeting content analysis.

```python
@dataclass
class MeetingSummary:
    key_phrases: List[KeyPhrase]
    topics: List[str]
    action_items: List[ActionItem]
    sentiment: Dict[str, float]
    entities: List[Dict[str, Any]]
    summary_text: str
```

### AzureConfig

Azure service configuration.

```python
@dataclass
class AzureConfig:
    speech_key: str
    speech_region: str
    text_analytics_key: str
    text_analytics_endpoint: str
    storage_connection_string: Optional[str] = None
    storage_container_name: Optional[str] = None
```

### ProcessingConfig

Audio processing configuration.

```python
@dataclass
class ProcessingConfig:
    default_language: str = "en-US"
    enable_diarization: bool = True
    max_speakers: int = 10
    sample_rate: int = 16000
    channels: int = 1
    apply_noise_reduction: bool = True
```

---

## Error Handling

All methods may raise standard Python exceptions:

- `FileNotFoundError`: When input files don't exist
- `RuntimeError`: For processing failures
- `ValueError`: For invalid configuration or parameters
- `ImportError`: When required dependencies are missing

**Example with error handling:**

```python
try:
    processor = MeetingProcessor()
    results = processor.process_audio_file("meeting.wav")
except FileNotFoundError as e:
    print(f"File not found: {e}")
except RuntimeError as e:
    print(f"Processing failed: {e}")
except ValueError as e:
    print(f"Configuration error: {e}")
```

---

## Configuration

### Environment Variables

Configure the application using environment variables:

```bash
# Required
AZURE_SPEECH_KEY=your_speech_service_key
AZURE_SPEECH_REGION=your_region
AZURE_TEXT_ANALYTICS_KEY=your_text_analytics_key
AZURE_TEXT_ANALYTICS_ENDPOINT=https://your-resource.cognitiveservices.azure.com/

# Optional
DEFAULT_LANGUAGE=en-US
ENABLE_SPEAKER_DIARIZATION=true
MAX_SPEAKERS=10
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
APPLY_NOISE_REDUCTION=true
```

### ConfigManager Usage

```python
from meeting_processor.utils import ConfigManager

# Load from .env file
config = ConfigManager()

# Load from custom file
config = ConfigManager(env_file="custom.env")

# Get configurations
azure_config = config.get_azure_config()
processing_config = config.get_processing_config()

# Validate configuration
if not config.validate_config():
    print("Invalid configuration")
```

---

## Logging

Configure logging for the application:

```python
from meeting_processor.utils import setup_logging

# Basic setup
setup_logging(level="INFO")

# With file output
setup_logging(
    level="DEBUG",
    log_file="meeting_processor.log"
)
```

**Log Levels:**
- `DEBUG`: Detailed information for debugging
- `INFO`: General informational messages
- `WARNING`: Warning messages
- `ERROR`: Error messages
- `CRITICAL`: Critical errors

---

## Examples

### Complete Example

```python
from meeting_processor.pipeline import MeetingProcessor
from meeting_processor.utils import ConfigManager, setup_logging
import json

# Setup logging
setup_logging(level="INFO")

# Initialize processor
config = ConfigManager()
processor = MeetingProcessor(config)

# Process audio file
results = processor.process_audio_file(
    "meeting.wav",
    output_dir="./output"
)

# Access transcription
transcription = results["transcription"]
print(f"Duration: {transcription['duration']} seconds")
print(f"Speakers: {transcription['metadata']['speaker_count']}")

# Access summary
summary = results["summary"]
print(f"Topics: {', '.join(summary['topics'])}")
print(f"Sentiment: {summary['sentiment']['overall']}")

# Save results
with open("results.json", "w") as f:
    json.dump(results, f, indent=2)
```

### Batch Processing Example

```python
import glob
from meeting_processor.pipeline import MeetingProcessor

processor = MeetingProcessor()

# Find all WAV files
audio_files = glob.glob("meetings/*.wav")

# Process in batch
results = processor.process_batch(
    audio_files,
    output_dir="./batch_results"
)

# Report statistics
successful = sum(1 for r in results if "error" not in r)
print(f"Processed {successful}/{len(results)} files successfully")
```
