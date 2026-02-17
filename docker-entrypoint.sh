#!/bin/bash
set -e

# Default environment variables (can be overridden at runtime)
: ${API_HOST:=0.0.0.0}
: ${API_PORT:=8000}

# Run uvicorn with exec to properly handle signals
exec python -m uvicorn meeting_processor.api.app:app --host "${API_HOST}" --port "${API_PORT}"
