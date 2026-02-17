FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY setup.py .

# Install the package
RUN pip install -e .

# Create temp directory for file processing
RUN mkdir -p /tmp/meeting_transcription

# Expose port
EXPOSE 8000

# Set default environment variables for secure binding
# Override API_HOST=0.0.0.0 in production deployments if needed
ENV API_HOST=127.0.0.1
ENV API_PORT=8000

# Run the application using Python module to respect environment variables
CMD ["python", "-m", "meeting_processor.api.app"]
