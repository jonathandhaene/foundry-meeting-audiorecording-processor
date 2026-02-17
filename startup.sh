#!/bin/bash

echo "Starting Meeting Transcription API..."

# Navigate to the application directory
cd /home/site/wwwroot

# Install any missing dependencies (if needed)
pip install --no-cache-dir -r requirements.txt

# Set default host to localhost for security
# Override with API_HOST=0.0.0.0 environment variable in Azure App Service if needed
export API_HOST=${API_HOST:-127.0.0.1}
export API_PORT=${API_PORT:-8000}

# Run the FastAPI application with Uvicorn using environment variables
python -m uvicorn meeting_processor.api.app:app --host ${API_HOST} --port ${API_PORT} --workers 4
