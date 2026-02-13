#!/bin/bash

echo "Starting Meeting Transcription API..."

# Navigate to the application directory
cd /home/site/wwwroot

# Install any missing dependencies (if needed)
pip install --no-cache-dir -r requirements.txt

# Run the FastAPI application with Uvicorn
python -m uvicorn meeting_processor.api.app:app --host 0.0.0.0 --port 8000 --workers 4
