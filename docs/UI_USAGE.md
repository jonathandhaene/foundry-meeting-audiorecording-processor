# Web UI Usage Guide

This guide explains how to use the Meeting Audio Transcription Web UI.

## Overview

The Web UI provides an intuitive interface for uploading audio files and transcribing them using different transcription methods (Azure Speech Services or Whisper).

## Features

- **File Upload**: Select a single audio file or multiple files for batch processing
- **Multiple Transcription Methods**:
  - Azure Speech Services (with speaker diarization)
  - Whisper Local (runs on your machine)
  - Whisper API (uses Azure OpenAI Whisper)
- **Configurable Options**:
  - Language selection or auto-detection
  - Speaker diarization (Azure only)
  - Whisper model size selection
  - NLP analysis toggle
  - **Chunk Size**: split large audio files into smaller segments for transcription
  - **Parallel Batch Processing**: process multiple files concurrently
  - **Max Concurrent Files**: control how many files are processed at the same time
- **Real-time Progress Tracking**: Monitor transcription status with pipeline stages
- **Results Display**: View transcriptions, segments, and NLP analysis
- **Job Management**: View, compare, and delete transcription jobs

## Setup

### 1. Backend Setup

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Configure environment variables in `.env`:

```bash
# Required for Azure Speech Services
AZURE_SPEECH_KEY=your_key
AZURE_SPEECH_REGION=your_region

# Required for NLP analysis
AZURE_TEXT_ANALYTICS_KEY=your_key
AZURE_TEXT_ANALYTICS_ENDPOINT=your_endpoint

# Optional: for Whisper API method
OPENAI_API_KEY=your_key
```

Start the backend server:

```bash
cd src/meeting_processor
python -m api.app
```

The API server will start on `http://localhost:8000`

### 2. Frontend Setup

Install Node.js dependencies:

```bash
cd frontend
npm install
```

Start the development server:

```bash
npm start
```

The UI will open at `http://localhost:3000`

## Using the UI

### Step 1: Upload Audio File(s)

1. Click "Choose File" or drag and drop an audio file
2. To process **multiple files**, hold Ctrl (Windows/Linux) or Cmd (macOS) and select several files, or use a file picker that supports multi-select
3. Supported formats: WAV, MP3, M4A, FLAC, etc.
4. File size limit depends on your server configuration

When multiple files are selected, the submit button changes to **"Start Batch (N files)"** and batch processing settings become active.

### Step 2: Select Transcription Method

Choose from:

- **Azure Speech Services**: Best for multi-speaker conversations with high accuracy
  - Supports speaker diarization
  - Requires Azure credentials
  
- **Whisper (Local)**: Runs on your machine
  - No API costs
  - Choose model size (tiny to large)
  - Larger models = more accurate but slower
  
- **Whisper (Azure OpenAI API)**: Uses Azure-hosted Whisper
  - Fast and accurate
  - Requires Azure OpenAI endpoint configured

### Step 3: Configure Options

#### Language
- Leave empty for auto-detection
- Or specify: `en-US`, `es-ES`, `fr-FR`, etc.

#### Speaker Diarization
- Enable to identify different speakers
- Only works with Azure Speech Services
- Automatically assigns speaker IDs

#### Whisper Model (Local only)
- **Tiny**: Fastest, least accurate
- **Base**: Good balance (recommended for testing)
- **Small**: Better accuracy
- **Medium**: High accuracy, slower
- **Large**: Best accuracy, slowest

#### NLP Analysis
- Enable to get:
  - Key phrases
  - Sentiment analysis
  - Entity recognition
  - Topic identification

#### ⚙️ Processing Settings

**Chunk Size (seconds)**
- Controls how audio is split before transcription
- **0 (Auto)**: Process the full file at once (default)
- Increase (e.g. 60, 120, 300 seconds) for very long recordings to reduce memory usage
- Useful when transcribing hour-long meetings with Whisper Local

**Enable parallel batch processing**
- Toggle on to process multiple files concurrently
- Only relevant when multiple files are selected
- Significantly reduces total time for large batches

**Max concurrent files**
- Appears when parallel batch processing is enabled
- Controls how many files are processed simultaneously (1–10)
- Recommended: 2–4; higher values use more CPU and memory

### Step 4: Transcribe (Single File) or Start Batch (Multiple Files)

Click **"Transcribe"** (single file) or **"Start Batch (N files)"** (multiple files) to start processing. Each file becomes a job in the jobs list with status:

- **Pending**: Queued for processing
- **Processing**: Currently transcribing (shows pipeline progress)
- **Completed**: Finished successfully
- **Failed**: Error occurred (shows error message)

### Step 5: View Results

When completed, the job card expands to show:

1. **Full Transcription**: Complete text
2. **Metadata**: Duration, language, speaker count
3. **Segments**: Individual speech segments with timestamps
   - Speaker IDs (if diarization enabled)
   - Start/end times
   - Text content
4. **NLP Analysis** (if enabled):
   - Key phrases
   - Overall sentiment
   - Entities

### Step 6: Compare Results

Run the same audio file with different methods to compare:
- Accuracy differences
- Processing time
- Speaker identification quality

### Job Management

- **Delete**: Remove a job and its results
- **Auto-refresh**: Jobs update automatically every 2 seconds
- **Persistent**: Jobs remain until deleted

## Tips

### Best Practices

1. **Audio Quality**: Better quality = better transcription
   - Use 16kHz sample rate
   - Mono audio preferred
   - Minimize background noise

2. **Method Selection**:
   - Use **Azure** for best speaker diarization
   - Use **Whisper Local** for no API costs
   - Use **Whisper API** for fastest processing

3. **Language**:
   - Specify language if known for better accuracy
   - Auto-detection works well for clear audio

4. **Model Size**:
   - Start with "base" for testing
   - Use "large" for production quality

5. **Chunk Size**:
   - Use `0` (Auto) for files under 30 minutes
   - Use `120`–`300` seconds for files over 1 hour to reduce memory pressure

6. **Batch Processing**:
   - Enable **parallel batch** and set **max concurrent = 2–4** for best throughput
   - Keep max concurrent ≤ available CPU cores to avoid resource contention

### Troubleshooting

**Upload fails:**
- Check file format is supported
- Verify backend server is running
- Check file size limits

**Processing stuck:**
- Refresh the page
- Check backend logs
- Verify API credentials are correct

**No speaker diarization:**
- Only works with Azure method
- Ensure "Enable Speaker Diarization" is checked
- Verify Azure Speech key is configured

**Whisper errors:**
- Local: Ensure models are downloaded (happens automatically first time)
- API: Verify Azure OpenAI endpoint is configured
- Check available disk space/memory

**Batch processing slow:**
- Enable "parallel batch processing"
- Increase "max concurrent files" (e.g., 3–4)
- Ensure the server has enough CPU cores

## API Endpoints

The UI interacts with these backend endpoints:

- `POST /api/transcribe`: Upload a single file and start transcription
- `POST /api/batch`: Upload multiple files and start batch transcription (supports `parallel_batch`, `max_concurrent`, `chunk_size`)
- `GET /api/jobs/{job_id}`: Get job status and results
- `GET /api/jobs`: List all jobs
- `DELETE /api/jobs/{job_id}`: Delete a job
- `GET /health`: Health check

## Production Deployment

### Docker Deployment

Build and run with Docker:

```bash
# Backend
docker build -t meeting-transcription-api .
docker run -p 8000:8000 --env-file .env meeting-transcription-api

# Frontend
cd frontend
docker build -t meeting-transcription-ui .
docker run -p 80:80 meeting-transcription-ui
```

### Azure App Service

1. Deploy backend as Azure App Service (Python)
2. Deploy frontend as Static Web App
3. Configure CORS in backend to allow frontend domain
4. Set environment variables in App Service configuration

See [DEPLOYMENT.md](../docs/DEPLOYMENT.md) for detailed deployment instructions.

## Security Considerations

1. **API Keys**: Never commit keys to version control
2. **CORS**: Configure allowed origins for production
3. **File Upload**: Implement file size limits
4. **Authentication**: Add user authentication for production
5. **HTTPS**: Always use HTTPS in production

## Support

For issues or questions:
1. Check backend logs: `tail -f app.log`
2. Check browser console for frontend errors
3. Verify API connectivity: `curl http://localhost:8000/health`
4. Open an issue on GitHub

## Examples

### Example 1: Quick Transcription

1. Upload: `meeting.wav`
2. Method: Azure Speech Services
3. Language: (auto-detect)
4. Diarization: ✓ Enabled
5. NLP: ✓ Enabled
6. Click "Transcribe"

Result: Transcription with speaker identification and content analysis

### Example 2: Long Recording with Chunking

1. Upload: `all-day-meeting.wav` (4-hour recording)
2. Method: Whisper Local
3. Model: medium
4. Chunk Size: **120 seconds** (slide to 120)
5. Click "Transcribe"

Result: Audio split into 2-minute chunks for memory-efficient transcription

### Example 3: Parallel Batch Processing

1. Select **multiple files** (e.g., `week1.wav`, `week2.wav`, `week3.wav`)
2. Method: Azure Speech Services
3. ⚙️ Processing Settings:
   - Enable parallel batch processing: ✓
   - Max concurrent files: **3**
4. Click "Start Batch (3 files)"

Result: All three files processed simultaneously, reducing total time by ~3×

### Example 4: Compare Methods

Run the same file with:
1. Azure (with diarization)
2. Whisper Local (base model)
3. Whisper API

Compare results for accuracy and processing time

### Example 5: Multi-language

1. Upload: `spanish-meeting.mp3`
2. Method: Whisper Local
3. Language: `es-ES` (Spanish)
4. Model: medium
5. Click "Transcribe"

Result: Accurate Spanish transcription with proper accents


## Setup

### 1. Backend Setup

Install Python dependencies:

```bash
pip install -r requirements.txt
```

Configure environment variables in `.env`:

```bash
# Required for Azure Speech Services
AZURE_SPEECH_KEY=your_key
AZURE_SPEECH_REGION=your_region

# Required for NLP analysis
AZURE_TEXT_ANALYTICS_KEY=your_key
AZURE_TEXT_ANALYTICS_ENDPOINT=your_endpoint

# Optional: for Whisper API method
OPENAI_API_KEY=your_key
```

Start the backend server:

```bash
cd src/meeting_processor
python -m api.app
```

The API server will start on `http://localhost:8000`

### 2. Frontend Setup

Install Node.js dependencies:

```bash
cd frontend
npm install
```

Start the development server:

```bash
npm start
```

The UI will open at `http://localhost:3000`

## Using the UI

### Step 1: Upload Audio File

1. Click "Choose File" or drag and drop an audio file
2. Supported formats: WAV, MP3, M4A, FLAC, etc.
3. File size limit depends on your server configuration

### Step 2: Select Transcription Method

Choose from:

- **Azure Speech Services**: Best for multi-speaker conversations with high accuracy
  - Supports speaker diarization
  - Requires Azure credentials
  
- **Whisper (Local)**: Runs on your machine
  - No API costs
  - Choose model size (tiny to large)
  - Larger models = more accurate but slower
  
- **Whisper (OpenAI API)**: Uses OpenAI's hosted Whisper
  - Fast and accurate
  - Requires OpenAI API key
  - Has usage costs

### Step 3: Configure Options

#### Language
- Leave empty for auto-detection
- Or specify: `en-US`, `es-ES`, `fr-FR`, etc.

#### Speaker Diarization
- Enable to identify different speakers
- Only works with Azure Speech Services
- Automatically assigns speaker IDs

#### Whisper Model (Local only)
- **Tiny**: Fastest, least accurate
- **Base**: Good balance (recommended for testing)
- **Small**: Better accuracy
- **Medium**: High accuracy, slower
- **Large**: Best accuracy, slowest

#### NLP Analysis
- Enable to get:
  - Key phrases
  - Sentiment analysis
  - Entity recognition
  - Topic identification

### Step 4: Transcribe

Click "Transcribe" to start processing. The job will appear in the jobs list with status:

- **Pending**: Queued for processing
- **Processing**: Currently transcribing (shows progress)
- **Completed**: Finished successfully
- **Failed**: Error occurred (shows error message)

### Step 5: View Results

When completed, the job card expands to show:

1. **Full Transcription**: Complete text
2. **Metadata**: Duration, language, speaker count
3. **Segments**: Individual speech segments with timestamps
   - Speaker IDs (if diarization enabled)
   - Start/end times
   - Text content
4. **NLP Analysis** (if enabled):
   - Key phrases
   - Overall sentiment
   - Entities

### Step 6: Compare Results

Run the same audio file with different methods to compare:
- Accuracy differences
- Processing time
- Speaker identification quality

### Job Management

- **Delete**: Remove a job and its results
- **Auto-refresh**: Jobs update automatically every 2 seconds
- **Persistent**: Jobs remain until deleted

## Tips

### Best Practices

1. **Audio Quality**: Better quality = better transcription
   - Use 16kHz sample rate
   - Mono audio preferred
   - Minimize background noise

2. **Method Selection**:
   - Use **Azure** for best speaker diarization
   - Use **Whisper Local** for no API costs
   - Use **Whisper API** for fastest processing

3. **Language**:
   - Specify language if known for better accuracy
   - Auto-detection works well for clear audio

4. **Model Size**:
   - Start with "base" for testing
   - Use "large" for production quality

### Troubleshooting

**Upload fails:**
- Check file format is supported
- Verify backend server is running
- Check file size limits

**Processing stuck:**
- Refresh the page
- Check backend logs
- Verify API credentials are correct

**No speaker diarization:**
- Only works with Azure method
- Ensure "Enable Speaker Diarization" is checked
- Verify Azure Speech key is configured

**Whisper errors:**
- Local: Ensure models are downloaded (happens automatically first time)
- API: Verify OPENAI_API_KEY is set
- Check available disk space/memory

## API Endpoints

The UI interacts with these backend endpoints:

- `POST /api/transcribe`: Upload file and start transcription
- `GET /api/jobs/{job_id}`: Get job status and results
- `GET /api/jobs`: List all jobs
- `DELETE /api/jobs/{job_id}`: Delete a job
- `GET /health`: Health check

## Production Deployment

### Docker Deployment

Build and run with Docker:

```bash
# Backend
docker build -t meeting-transcription-api .
docker run -p 8000:8000 --env-file .env meeting-transcription-api

# Frontend
cd frontend
docker build -t meeting-transcription-ui .
docker run -p 80:80 meeting-transcription-ui
```

### Azure App Service

1. Deploy backend as Azure App Service (Python)
2. Deploy frontend as Static Web App
3. Configure CORS in backend to allow frontend domain
4. Set environment variables in App Service configuration

See [DEPLOYMENT.md](../docs/DEPLOYMENT.md) for detailed deployment instructions.

## Security Considerations

1. **API Keys**: Never commit keys to version control
2. **CORS**: Configure allowed origins for production
3. **File Upload**: Implement file size limits
4. **Authentication**: Add user authentication for production
5. **HTTPS**: Always use HTTPS in production

## Support

For issues or questions:
1. Check backend logs: `tail -f app.log`
2. Check browser console for frontend errors
3. Verify API connectivity: `curl http://localhost:8000/health`
4. Open an issue on GitHub

## Examples

### Example 1: Quick Transcription

1. Upload: `meeting.wav`
2. Method: Azure Speech Services
3. Language: (auto-detect)
4. Diarization: ✓ Enabled
5. NLP: ✓ Enabled
6. Click "Transcribe"

Result: Transcription with speaker identification and content analysis

### Example 2: Compare Methods

Run the same file with:
1. Azure (with diarization)
2. Whisper Local (base model)
3. Whisper API

Compare results for accuracy and processing time

### Example 3: Multi-language

1. Upload: `spanish-meeting.mp3`
2. Method: Whisper Local
3. Language: `es-ES` (Spanish)
4. Model: medium
5. Click "Transcribe"

Result: Accurate Spanish transcription with proper accents
