# Meeting Audio Recording Processor

A comprehensive end-to-end solution for processing meeting audio files with multi-speaker, multilingual conversations. This project provides both a **Web UI** and **API** for easy audio transcription using multiple methods (Azure Speech Services, OpenAI Whisper), along with content analysis capabilities.

## Features

### 🎯 Core Features
- **Multiple Transcription Methods**:
  - Azure Speech Services (with speaker diarization)
  - OpenAI Whisper (local or API)
  - Configurable options for each method
- **Audio Preprocessing**: Automatic normalization and noise reduction using FFmpeg
- **Speaker Diarization**: Multi-speaker identification (Azure)
- **Multilingual Support**: Auto-detection or specify language
- **Content Understanding**: Azure Text Analytics for:
  - Key phrase extraction
  - Sentiment analysis
  - Entity recognition
  - Action item detection
  - Topic identification

### 🖥️ User Interface
- **Web UI**: Interactive React-based interface for easy file upload and transcription
- **REST API**: FastAPI backend for programmatic access
- **Real-time Progress**: Track transcription status and view results instantly
- **Job Management**: View, compare, and manage multiple transcription jobs

### 🚀 Deployment
- **Scalable**: Azure Functions for serverless processing
- **CI/CD Integration**: Automated testing and deployment with GitHub Actions
- **Docker Support**: Containerized deployment options

## Architecture

```
┌─────────────────┐
│   Web UI        │ (React Frontend)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI Server │ (REST API)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Audio Input    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Audio Processor │ (FFmpeg normalization)
└────────┬────────┘
         │
         ├──────────────┬──────────────┐
         ▼              ▼              ▼
┌──────────────┐  ┌──────────┐  ┌──────────┐
│Azure Speech  │  │ Whisper  │  │ Whisper  │
│   Services   │  │  Local   │  │   API    │
└──────┬───────┘  └─────┬────┘  └─────┬────┘
       │                │              │
       └────────────────┴──────────────┘
                        │
                        ▼
                ┌───────────────┐
                │ Azure Text    │ (Content Understanding)
                │  Analytics    │
                └───────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │  Structured   │
                │    Output     │
                └───────────────┘
```
```

## Prerequisites

- Python 3.9 or higher
- Node.js 16+ (for Web UI)
- FFmpeg (for audio processing)
- Azure subscription with:
  - Azure Speech Services resource
  - Azure Text Analytics resource
  - (Optional) Azure Storage Account
  - (Optional) Azure Functions app
- (Optional) OpenAI API key for Whisper API method

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/jonathandhaene/foundry-meeting-audiorecording-processor.git
cd foundry-meeting-audiorecording-processor
```

### 2. Install FFmpeg

#### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

#### macOS
```bash
brew install ffmpeg
```

#### Windows
Download from [FFmpeg official website](https://ffmpeg.org/download.html)

### 3. Install Python dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 4. Configure services

Copy the example environment file and fill in your credentials:

```bash
cp .env.example .env
```

Edit `.env` with your service credentials:

```ini
# Required for Azure Speech Services
AZURE_SPEECH_KEY=your_speech_service_key
AZURE_SPEECH_REGION=your_region  # e.g., eastus

# Required for NLP analysis
AZURE_TEXT_ANALYTICS_KEY=your_text_analytics_key
AZURE_TEXT_ANALYTICS_ENDPOINT=https://your-resource.cognitiveservices.azure.com/

# Optional: for Whisper API transcription
OPENAI_API_KEY=your_openai_api_key
```

### 5. Install Frontend dependencies (for Web UI)

```bash
cd frontend
npm install
cd ..
```

## Quick Start

### Option 1: Web UI (Recommended)

**Start the backend server:**

```bash
# Activate virtual environment if not already active
source venv/bin/activate

# Start FastAPI server
python -m meeting_processor.api.app
```

The API will be available at `http://localhost:8000`

**Start the frontend (in a new terminal):**

```bash
cd frontend
npm start
```

The Web UI will open at `http://localhost:3000`

**Using the UI:**
1. Upload an audio file
2. Select transcription method (Azure, Whisper Local, or Whisper API)
3. Configure options (language, diarization, model size)
4. Click "Transcribe"
5. View results in real-time

For detailed UI usage instructions, see [docs/UI_USAGE.md](docs/UI_USAGE.md)

### Option 2: Command Line Usage

Process a single audio file:

```bash
python -m meeting_processor.pipeline audio_file.wav
```

With custom output directory:

```bash
python -m meeting_processor.pipeline audio_file.wav --output ./output
```

Skip audio preprocessing (if already normalized):

```bash
python -m meeting_processor.pipeline audio_file.wav --skip-preprocessing
```

### Python API Usage

```python
from meeting_processor.pipeline import MeetingProcessor
from meeting_processor.utils import ConfigManager

# Initialize processor
config = ConfigManager()
processor = MeetingProcessor(config)

# Process audio file
results = processor.process_audio_file(
    "meeting.wav",
    output_dir="./output"
)

# Access results
print("Transcription:", results["transcription"]["full_text"])
print("Key Topics:", results["summary"]["topics"])
print("Action Items:", results["summary"]["action_items"])
```

### Batch Processing

```python
from meeting_processor.pipeline import MeetingProcessor

processor = MeetingProcessor()

audio_files = ["meeting1.wav", "meeting2.wav", "meeting3.wav"]
results = processor.process_batch(audio_files, output_dir="./batch_output")
```

## Output Format

The processor generates three main output files for each input:

### 1. Transcription JSON (`*_transcription.json`)

```json
{
  "segments": [
    {
      "text": "Hello everyone, welcome to the meeting",
      "start_time": 0.0,
      "end_time": 3.5,
      "speaker_id": "Guest-1",
      "confidence": 0.95
    }
  ],
  "full_text": "Complete transcription...",
  "duration": 1800.0,
  "language": "en-US",
  "metadata": {
    "diarization_enabled": true,
    "speaker_count": 5,
    "speakers": ["Guest-1", "Guest-2", "Guest-3", "Guest-4", "Guest-5"]
  }
}
```

### 2. Summary JSON (`*_summary.json`)

```json
{
  "key_phrases": [
    {"text": "machine learning", "score": 0.95},
    {"text": "data processing", "score": 0.90}
  ],
  "topics": ["AI", "Development", "Project Timeline"],
  "action_items": [
    {
      "text": "Review the documentation",
      "assignee": null,
      "due_date": null
    }
  ],
  "sentiment": {
    "positive": 0.7,
    "neutral": 0.25,
    "negative": 0.05,
    "overall": "positive"
  },
  "entities": [
    {
      "text": "Microsoft",
      "category": "Organization",
      "confidence": 0.98
    }
  ],
  "summary_text": "Meeting summary..."
}
```

### 3. Complete Results (`*_results.json`)

Contains all processing results including file paths and metadata.

## Azure Functions Deployment

### Local Testing

```bash
cd azure_functions
func start
```

### Deploy to Azure

1. Create an Azure Functions app:

```bash
az functionapp create \
  --resource-group myResourceGroup \
  --consumption-plan-location eastus \
  --runtime python \
  --runtime-version 3.11 \
  --functions-version 4 \
  --name myMeetingProcessorApp \
  --storage-account mystorageaccount
```

2. Configure application settings:

```bash
az functionapp config appsettings set \
  --name myMeetingProcessorApp \
  --resource-group myResourceGroup \
  --settings \
    AZURE_SPEECH_KEY=your_key \
    AZURE_SPEECH_REGION=eastus \
    AZURE_TEXT_ANALYTICS_KEY=your_key \
    AZURE_TEXT_ANALYTICS_ENDPOINT=your_endpoint
```

3. Deploy:

```bash
func azure functionapp publish myMeetingProcessorApp
```

Or use GitHub Actions (see CI/CD section below).

## Testing

### Run all tests

```bash
pytest
```

### Run specific test suites

```bash
# Unit tests only
pytest tests/unit/

# Integration tests
pytest tests/integration/

# With coverage
pytest --cov=meeting_processor --cov-report=html
```

### Run linting and type checking

```bash
# Linting
flake8 src/

# Type checking
mypy src/ --ignore-missing-imports

# Code formatting
black src/ tests/
```

## CI/CD with GitHub Actions

The repository includes automated CI/CD pipelines:

### Continuous Integration

Triggered on push and pull requests:
- Runs tests on multiple Python versions (3.9, 3.10, 3.11)
- Performs linting and type checking
- Generates coverage reports

### Deployment

Automatic deployment to Azure Functions on push to `main` branch.

Required GitHub Secrets:
- `AZURE_CREDENTIALS`: Azure service principal credentials
- `AZURE_FUNCTION_APP_NAME`: Name of your Azure Functions app
- `AZURE_FUNCTION_PUBLISH_PROFILE`: Azure Functions publish profile

### Security Scanning

Weekly security scans using:
- Safety (dependency vulnerability scanning)
- Bandit (code security analysis)

## Configuration Options

### Audio Processing

- `AUDIO_SAMPLE_RATE`: Target sample rate (default: 16000 Hz)
- `AUDIO_CHANNELS`: Number of channels (default: 1 for mono)
- `APPLY_NOISE_REDUCTION`: Enable noise reduction (default: true)

### Speech Recognition

- `DEFAULT_LANGUAGE`: Primary language code (default: en-US)
- `ENABLE_SPEAKER_DIARIZATION`: Enable speaker identification (default: true)
- `MAX_SPEAKERS`: Maximum number of speakers (default: 10)

## Performance Considerations

- **Audio File Size**: Larger files take longer to process. Consider splitting very long recordings.
- **Sample Rate**: 16 kHz is optimal for speech recognition. Higher rates don't improve accuracy significantly.
- **Network Latency**: Azure API calls require internet connectivity. Processing time depends on network speed.
- **Concurrent Processing**: For batch processing, consider implementing parallel processing with appropriate rate limiting.

## Troubleshooting

### FFmpeg Not Found

Ensure FFmpeg is installed and in your system PATH:

```bash
ffmpeg -version
```

### Azure API Errors

- Verify your API keys are correct
- Check your Azure subscription quota and usage limits
- Ensure your Azure region supports the required services

### Import Errors

Make sure you've installed all dependencies:

```bash
pip install -r requirements.txt
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please open an issue on GitHub.

## Acknowledgments

- Microsoft Azure Cognitive Services
- Azure Speech Services team
- FFmpeg project
- Python community

## References

- [Azure Speech Services Documentation](https://docs.microsoft.com/azure/cognitive-services/speech-service/)
- [Azure Text Analytics Documentation](https://docs.microsoft.com/azure/cognitive-services/text-analytics/)
- [Azure Functions Python Developer Guide](https://docs.microsoft.com/azure/azure-functions/functions-reference-python)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)