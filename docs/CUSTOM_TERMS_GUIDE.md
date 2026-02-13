# Custom Terms and Multi-language Transcription Guide

This guide explains how to use custom terminology and multi-language support features to improve transcription accuracy for domain-specific content and mixed-language audio.

## Table of Contents

- [Overview](#overview)
- [Custom Terms Feature](#custom-terms-feature)
- [Multi-language Support](#multi-language-support)
- [Usage Examples](#usage-examples)
- [Best Practices](#best-practices)
- [API Reference](#api-reference)

## Overview

The Meeting Audio Transcription service now supports:

1. **Custom Terms**: Define domain-specific vocabulary, technical jargon, proper nouns, and terminology to improve recognition accuracy
2. **Multi-language Support**: Handle audio containing multiple languages (e.g., Dutch with English technical terms)

These features work with both Azure Speech Services and OpenAI Whisper transcription engines.

## Custom Terms Feature

### What are Custom Terms?

Custom terms are words or phrases that you want the transcription engine to recognize with higher accuracy. These are particularly useful for:

- **Technical terminology**: Kubernetes, MLOps, DevOps, API names
- **Proper nouns**: Company names, product names, person names
- **Industry jargon**: Domain-specific vocabulary
- **Acronyms**: AWS, CI/CD, SaaS, etc.
- **Foreign words**: Non-English words in otherwise English content

### How It Works

#### Azure Speech Services
Azure uses **Phrase List Grammar** to boost recognition of specific words and phrases. When you provide custom terms:
- The engine gives higher priority to these terms during recognition
- Improves accuracy for domain-specific vocabulary
- Works in real-time during transcription

#### OpenAI Whisper
Whisper uses an **initial prompt** mechanism. Your custom terms are included in a context prompt that guides the model:
- The prompt provides context about expected vocabulary
- Helps the model recognize specialized terms
- Works for both local and API-based Whisper transcription

### Providing Custom Terms

#### Option 1: Text Input (Web UI)

Use the text area in the web interface:

```
Kubernetes, Docker, Terraform, Azure DevOps, MLOps, CI/CD, Prometheus, Grafana
```

You can use:
- Comma-separated values
- One term per line
- Mix of both

#### Option 2: File Upload (Web UI)

Create a text file with one term per line:

```text
Kubernetes
Docker
Terraform
Azure DevOps
MLOps
Prometheus
Grafana
GitOps
ArgoCD
Helm
```

Save as `custom_terms.txt` and upload via the file input.

#### Option 3: API Request

Include custom terms in your API request:

```bash
curl -X POST "http://localhost:8000/api/transcribe" \
  -F "file=@meeting.wav" \
  -F "method=azure" \
  -F "custom_terms=Kubernetes,Docker,MLOps,Azure DevOps"
```

Or upload a terms file:

```bash
curl -X POST "http://localhost:8000/api/transcribe" \
  -F "file=@meeting.wav" \
  -F "method=whisper_local" \
  -F "terms_file=@custom_terms.txt"
```

#### Option 4: Python API

```python
from meeting_processor.transcription import AzureSpeechTranscriber, WhisperTranscriber

# Define custom terms
custom_terms = [
    "Kubernetes",
    "Docker",
    "Terraform",
    "Azure DevOps",
    "MLOps",
    "CI/CD"
]

# Azure Speech Services
azure_transcriber = AzureSpeechTranscriber(
    speech_key="your_key",
    speech_region="eastus",
    custom_terms=custom_terms
)

result = azure_transcriber.transcribe_audio("meeting.wav")

# Whisper (local or API)
whisper_transcriber = WhisperTranscriber(
    model_size="base",
    custom_terms=custom_terms,
    use_api=False
)

result = whisper_transcriber.transcribe_audio("meeting.wav")
```

## Multi-language Support

### What is Multi-language Support?

This feature allows transcription of audio containing multiple languages in a single recording. It's particularly useful for:

- Meetings with international participants
- Content mixing local language with English technical terms (e.g., Dutch + English)
- Multilingual presentations
- Code-switching in conversations

### How It Works (Azure Speech Services)

Azure Speech Services supports **automatic language detection** from a list of candidate languages. When you specify language candidates:
- The engine automatically detects which language is being spoken
- Switches between languages seamlessly
- Optimizes recognition for mixed-language content

**Note**: Multi-language detection requires at least 2 language candidates.

### Specifying Language Candidates

#### Web UI

Enter comma-separated language codes in the "Multi-language Support" field:

```
en-US,nl-NL
```

For Dutch meetings with English terms:
```
nl-NL,en-US
```

For multilingual European meeting:
```
en-US,de-DE,fr-FR
```

#### API Request

```bash
curl -X POST "http://localhost:8000/api/transcribe" \
  -F "file=@meeting.wav" \
  -F "method=azure" \
  -F "language_candidates=nl-NL,en-US"
```

#### Python API

```python
from meeting_processor.transcription import AzureSpeechTranscriber

# For Dutch with English technical terms
transcriber = AzureSpeechTranscriber(
    speech_key="your_key",
    speech_region="eastus",
    language_candidates=["nl-NL", "en-US"]
)

result = transcriber.transcribe_audio("meeting.wav")
```

### Supported Language Codes

Common language codes include:

| Language | Code |
|----------|------|
| English (US) | en-US |
| English (UK) | en-GB |
| Dutch (Netherlands) | nl-NL |
| German | de-DE |
| French | fr-FR |
| Spanish | es-ES |
| Italian | it-IT |
| Portuguese | pt-BR |
| Japanese | ja-JP |
| Chinese (Mandarin) | zh-CN |

For a complete list, see [Azure Speech Services Language Support](https://docs.microsoft.com/azure/cognitive-services/speech-service/language-support).

## Usage Examples

### Example 1: Technical Meeting with Custom Terms

You're transcribing a DevOps team meeting discussing Kubernetes and CI/CD:

**Custom Terms:**
```
Kubernetes, kubectl, Helm, ArgoCD, GitOps, Prometheus, Grafana, 
Istio, Jenkins, GitHub Actions, Docker, Terraform
```

**Result:** The transcription will correctly recognize these technical terms instead of mishearing them as common words.

### Example 2: Dutch Meeting with English Technical Terms

A Dutch software development meeting where participants use English technical vocabulary:

**Settings:**
- Primary language: `nl-NL` (Dutch)
- Language candidates: `nl-NL,en-US`
- Custom terms: `API, REST, microservices, Docker, Kubernetes, database, frontend, backend`

**Result:** The transcription will correctly handle Dutch sentences with embedded English technical terms.

### Example 3: Product Demo with Company-Specific Terms

A product demonstration mentioning company and product names:

**Custom Terms:**
```
Acme Corporation, WidgetMaster Pro, CloudSync, DataHub, 
QuickAnalytics, TechSupport Plus, CustomerConnect
```

**Result:** Proper nouns and product names are transcribed accurately.

### Example 4: Medical Conference

A medical conference with specialized terminology:

**Custom Terms:**
```
myocardial infarction, echocardiogram, percutaneous coronary intervention,
electrocardiogram, angioplasty, stent, thrombolysis, coronary artery bypass,
cardiac catheterization, anticoagulation
```

**Result:** Medical terms are recognized correctly, avoiding common misrecognitions.

## Best Practices

### Custom Terms

1. **Be Specific**: Include exact terms as they should appear in the transcript
2. **Include Variations**: Add both singular and plural forms if needed
3. **Prioritize**: Focus on the most important terms (20-50 terms is ideal)
4. **Use Proper Capitalization**: Include terms as they should be written
5. **Test Iteratively**: Start with key terms, review results, add more as needed

### Multi-language Support

1. **Order Matters**: Put the primary language first in the candidates list
2. **Limit Languages**: 2-4 language candidates work best for accuracy
3. **Combine with Custom Terms**: Use both features together for best results
4. **Test Different Combinations**: Experiment with different language orders

### General Tips

1. **Audio Quality**: Clean audio produces better results, regardless of custom terms
2. **Context Helps**: Provide a brief description or context when possible
3. **Review and Refine**: Check transcription results and refine your term list
4. **Domain-Specific Lists**: Maintain term lists for different use cases (IT, medical, legal, etc.)

## API Reference

### Transcription Request Parameters

| Parameter | Type | Description | Example |
|-----------|------|-------------|---------|
| `custom_terms` | string | Comma or newline-separated terms | `"Docker,Kubernetes,API"` |
| `terms_file` | file | Text file with terms (one per line) | `custom_terms.txt` |
| `language_candidates` | string | Comma-separated language codes | `"nl-NL,en-US"` |

### Response Metadata

Transcription results include metadata about custom terms usage:

```json
{
  "metadata": {
    "custom_terms_count": 15,
    "language_candidates": ["nl-NL", "en-US"],
    "diarization_enabled": true,
    "speaker_count": 3
  }
}
```

### Python API Classes

#### AzureSpeechTranscriber

```python
class AzureSpeechTranscriber:
    def __init__(
        self,
        speech_key: str,
        speech_region: str,
        language: str = "en-US",
        enable_diarization: bool = True,
        max_speakers: int = 10,
        custom_terms: Optional[List[str]] = None,
        language_candidates: Optional[List[str]] = None
    )
```

#### WhisperTranscriber

```python
class WhisperTranscriber:
    def __init__(
        self,
        model_size: str = "base",
        language: Optional[str] = None,
        use_api: bool = False,
        api_key: Optional[str] = None,
        custom_terms: Optional[List[str]] = None
    )
```

## Troubleshooting

### Custom Terms Not Working

- Verify terms are spelled correctly
- Check that terms are appropriate for the audio content
- Try reducing the number of terms (start with top 20)
- Ensure audio quality is good

### Multi-language Detection Issues

- Verify you've specified at least 2 language candidates
- Check that language codes are correct
- Ensure sufficient audio in each language (at least a few seconds)
- Try reordering language candidates

### Performance Considerations

- Custom terms add minimal processing overhead
- Multi-language detection may slightly increase processing time
- Whisper local models: larger models give better results with custom terms
- For large-scale processing, consider batching and parallel processing

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub
- Check the main README for general usage
- Review the API documentation in `/docs/API.md`

## Related Documentation

- [Main README](../README.md)
- [API Documentation](API.md)
- [UI Usage Guide](UI_USAGE.md)
- [Azure Setup Guide](AZURE_SETUP.md)
