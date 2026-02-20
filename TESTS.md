# Test Documentation

## Overview

The test suite covers unit and integration tests for the Meeting Audio Recording Processor. All 105 tests pass successfully.

| Category    | Count |
|-------------|-------|
| Unit tests  | 102   |
| Integration tests | 3 |
| **Total**   | **105** |

## Running Tests

### Prerequisites

Install dependencies:

```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### Run all tests

```bash
pytest tests/ -v
```

### Run unit tests only

```bash
pytest tests/unit/ -v
```

### Run integration tests only

```bash
pytest tests/integration/ -v
```

### Run with coverage report

```bash
pytest tests/unit/ -v --cov=meeting_processor --cov-report=term --cov-report=html
```

### Run a specific test file

```bash
pytest tests/unit/test_api.py -v
```

## Test Structure

```
tests/
├── conftest.py                        # Shared fixtures and session setup
├── fixtures/
│   └── __init__.py
├── unit/
│   ├── test_api.py                    # FastAPI endpoint tests
│   ├── test_audio_preprocessor.py     # Audio preprocessing tests
│   ├── test_config.py                 # Configuration management tests
│   ├── test_hf_transcriber.py         # HuggingFace transcriber tests
│   ├── test_nlp_analyzer.py           # NLP content analyzer tests
│   ├── test_pipeline_batch.py         # Batch pipeline tests
│   ├── test_transcriber.py            # Azure Speech transcriber tests
│   └── test_whisper_transcriber.py    # Whisper transcriber tests
└── integration/
    └── test_pipeline_integration.py   # End-to-end pipeline tests
```

## CI/CD Integration

Tests run automatically in the CI/CD pipeline (`.github/workflows/ci-cd.yml`) on every push or pull request to `main` or `develop` branches, across Python 3.10 and 3.11.

The pipeline includes:
1. **Linting** – `flake8 src/`
2. **Type checking** – `mypy src/ --ignore-missing-imports`
3. **Unit tests** – `pytest tests/unit/ -v --cov=meeting_processor --cov-report=xml`
4. **Coverage upload** – via `codecov/codecov-action`

## Environment Setup for Tests

Tests automatically use a temporary directory for `TRANSCRIPTION_DIR` (set in `conftest.py`) to avoid requiring write access to `/home/meeting_transcription`.

To run tests in an environment where `/home/meeting_transcription` is writable (e.g., production), set the environment variable explicitly:

```bash
export TRANSCRIPTION_DIR=/home/meeting_transcription
pytest tests/ -v
```

## Areas Refactored / Tests Fixed

The following issues were identified and resolved to achieve 100% test pass rate:

### Source Code Changes

1. **`src/meeting_processor/api/app.py`** – `PersistentJobStore` and `AUDIO_DIR` now read the `TRANSCRIPTION_DIR` environment variable (defaulting to `./meeting_transcription`) instead of hardcoding `/home/meeting_transcription`. This fixes a `PermissionError` during test collection in CI environments.

2. **`src/meeting_processor/utils/config.py`** – `validate_config()` now returns `False` when neither `AZURE_SPEECH_KEY` nor `AZURE_SPEECH_RESOURCE_ID` is configured, accurately reflecting a misconfigured environment.

### Test Changes

3. **`tests/conftest.py`** – Added module-level `TRANSCRIPTION_DIR` environment variable set to a temporary directory, preventing the `PermissionError` on `/home/meeting_transcription` during test collection.

4. **`tests/unit/test_api.py`** – Fixed `test_process_transcription_failure` to mock `normalize_audio` (the method actually called) instead of `preprocess_audio` (which doesn't exist).

5. **`tests/unit/test_config.py`** – Updated `test_missing_required_config` to assert on returned `None` values instead of incorrectly expecting a `ValueError` from `get_azure_config()`.

6. **`tests/unit/test_nlp_analyzer.py`** – Replaced `test_generate_summary` (called non-existent `_generate_summary`) with a test for `_fallback_summary`; replaced `test_categorize_content` (called non-existent `categorize_content`) with `test_extract_topics`.

7. **`tests/unit/test_whisper_transcriber.py`** – Updated `test_transcribe_api`, `test_transcribe_api_with_language`, and `test_transcribe_api_with_custom_terms` to mock the OpenAI v1 client API (`client.audio.transcriptions.create`) instead of the removed v0 API (`openai.Audio.transcribe`).
