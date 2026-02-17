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
# In Docker, default to 0.0.0.0 since container networking provides isolation
# Override at runtime with -e API_HOST=<value> if needed
ENV API_HOST=0.0.0.0
ENV API_PORT=8000

# Run the application using shell form to enable env var substitution
CMD python -m uvicorn meeting_processor.api.app:app --host ${API_HOST} --port ${API_PORT}
