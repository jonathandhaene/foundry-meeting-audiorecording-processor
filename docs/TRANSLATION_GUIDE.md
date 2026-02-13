# Translation Guide

This guide explains how to add or update translations for the Meeting Audio Transcription UI.

## Overview

The application uses [react-i18next](https://react.i18next.com/) for internationalization, supporting all 24 official EU languages:

- **Core Languages with Full Translations**: English (en), French (fr), German (de), Spanish (es), Italian (it), Portuguese (pt), Polish (pl), Dutch (nl)
- **Additional EU Languages** (with placeholder translations): Bulgarian (bg), Czech (cs), Danish (da), Greek (el), Estonian (et), Finnish (fi), Irish (ga), Croatian (hr), Hungarian (hu), Lithuanian (lt), Latvian (lv), Maltese (mt), Romanian (ro), Slovak (sk), Slovenian (sl), Swedish (sv)

## Directory Structure

Translation files are organized by language code in the `frontend/public/locales/` directory:

```
frontend/public/locales/
├── en/
│   └── translation.json
├── fr/
│   └── translation.json
├── de/
│   └── translation.json
├── es/
│   └── translation.json
└── ... (other languages)
```

## Translation File Format

Each translation file is a JSON object with nested keys organized by feature area:

```json
{
  "app": {
    "title": "Meeting Audio Transcription",
    "subtitle": "Upload audio files and transcribe using Azure Speech or Whisper"
  },
  "upload": {
    "title": "Upload & Configure",
    "audioFile": "Audio File:",
    "fileSelected": "Selected: {{filename}}"
  },
  "errors": {
    "noFile": "Please select an audio file",
    "uploadFailed": "Failed to submit transcription job"
  }
}
```

### Key Features

1. **Nested Structure**: Keys are organized hierarchically (e.g., `app.title`, `upload.audioFile`)
2. **Variable Interpolation**: Use `{{variableName}}` for dynamic content (e.g., `{{filename}}`, `{{count}}`)
3. **Consistent Keys**: All languages use the same key structure

## Adding a New Language

To add support for a new language:

1. **Create the directory** in `frontend/public/locales/`:
   ```bash
   mkdir -p frontend/public/locales/[language-code]
   ```

2. **Copy the English translation** as a starting point:
   ```bash
   cp frontend/public/locales/en/translation.json frontend/public/locales/[language-code]/translation.json
   ```

3. **Translate all values** in the JSON file, keeping keys unchanged:
   ```json
   {
     "app": {
       "title": "Your translated title",
       "subtitle": "Your translated subtitle"
     }
   }
   ```

4. **Add the language to the selector** in `frontend/src/LanguageSelector.js`:
   ```javascript
   const languages = [
     // ... existing languages
     { code: 'xx', name: 'Language Name' },
   ];
   ```

5. **Test the translation** by selecting it in the UI

## Updating Existing Translations

To update an existing translation:

1. **Locate the translation file**: `frontend/public/locales/[language-code]/translation.json`

2. **Find the key** you want to update in the JSON structure

3. **Update the value**, preserving any variable placeholders like `{{filename}}`

4. **Save and reload** the application to see changes

## Translation Guidelines

### Best Practices

1. **Keep it concise**: UI text should be brief and clear
2. **Maintain consistency**: Use the same terms throughout (e.g., "Transcription" vs "Transcript")
3. **Preserve variables**: Never translate variable names in `{{brackets}}`
4. **Test special characters**: Ensure proper rendering of language-specific characters
5. **Context matters**: Consider the UI context when translating (button labels vs descriptions)

### Variable Interpolation

Variables are replaced at runtime with dynamic content:

```json
{
  "upload": {
    "fileSelected": "Selected: {{filename}}"
  }
}
```

In French:
```json
{
  "upload": {
    "fileSelected": "Sélectionné: {{filename}}"
  }
}
```

### Pluralization

For count-based text, use the `count` variable:

```json
{
  "results": {
    "segments": {
      "title": "Segments ({{count}}):",
      "more": "... and {{count}} more segments"
    }
  }
}
```

## Translation Keys Reference

### Application Structure (`app`)
- `app.title`: Main page title
- `app.subtitle`: Page description

### Upload Section (`upload`)
- `upload.title`: Section title
- `upload.audioFile`: Audio file input label
- `upload.fileSelected`: File selection confirmation
- `upload.method`: Transcription method selector
- `upload.whisperModel`: Whisper model selector
- `upload.language`: Language input field
- `upload.languagePlaceholder`: Language input placeholder
- `upload.languageCandidates`: Multi-language support field
- `upload.languageCandidatesPlaceholder`: Multi-language placeholder
- `upload.languageCandidatesHelp`: Help text for multi-language
- `upload.customTerms`: Custom terms textarea
- `upload.customTermsPlaceholder`: Custom terms placeholder
- `upload.customTermsHelp`: Help text for custom terms
- `upload.termsFile`: Terms file upload label
- `upload.termsFileSelected`: Terms file confirmation
- `upload.termsFileHelp`: Help text for terms file
- `upload.enableDiarization`: Speaker diarization checkbox
- `upload.azureOnly`: Azure-only indicator
- `upload.enableNlp`: NLP analysis checkbox
- `upload.uploadButton`: Submit button text
- `upload.uploadingButton`: Loading state text

### Methods (`methods`)
- `methods.azure`: Azure Speech Services
- `methods.whisper_local`: Whisper (Local)
- `methods.whisper_api`: Whisper (OpenAI API)

### Whisper Models (`whisperModels`)
- `whisperModels.tiny`: Tiny model description
- `whisperModels.base`: Base model
- `whisperModels.small`: Small model
- `whisperModels.medium`: Medium model
- `whisperModels.large`: Large model description

### Jobs Section (`jobs`)
- `jobs.title`: Section title
- `jobs.noJobs`: Empty state message
- `jobs.method`: Method label
- `jobs.id`: Job ID label
- `jobs.progress`: Progress label
- `jobs.error`: Error label
- `jobs.deleteButton`: Delete button

### Job Status (`status`)
- `status.pending`: Pending status
- `status.processing`: Processing status
- `status.completed`: Completed status
- `status.failed`: Failed status

### Results Section (`results`)
- `results.title`: Results title
- `results.metadata.duration`: Duration label
- `results.metadata.language`: Language label
- `results.metadata.speakers`: Speakers label
- `results.metadata.customTerms`: Custom terms label
- `results.metadata.multiLanguage`: Multi-language label
- `results.segments.title`: Segments title (with count)
- `results.segments.more`: More segments text (with count)
- `results.nlp.title`: NLP analysis title
- `results.nlp.keyPhrases`: Key phrases label
- `results.nlp.sentiment`: Sentiment label

### Errors (`errors`)
- `errors.noFile`: No file selected error
- `errors.uploadFailed`: Upload failure error

### Language Selector (`languageSelector`)
- `languageSelector.label`: Dropdown label
- `languageSelector.tooltip`: Dropdown tooltip

## Testing Translations

### Manual Testing

1. Start the development server:
   ```bash
   cd frontend
   npm start
   ```

2. Open the application in your browser

3. Use the language selector in the top-right corner

4. Verify:
   - All text displays correctly
   - No missing translations (check console for warnings)
   - Special characters render properly
   - Variable interpolation works
   - Text fits in UI components

### Automated Testing

The build process checks for syntax errors in translation files:

```bash
cd frontend
npm run build
```

## Common Issues

### Missing Translations

If you see an English key instead of translated text:
- Check that the key exists in your translation file
- Verify the JSON structure matches the English file
- Ensure there are no syntax errors (commas, brackets)

### Special Characters Not Rendering

- Ensure your JSON file is saved with UTF-8 encoding
- Verify the characters display correctly in your editor
- Test in multiple browsers

### Variables Not Replaced

- Check that variable names match exactly (case-sensitive)
- Ensure variables are wrapped in double curly braces: `{{variable}}`
- Variables must not be translated (e.g., keep `{{filename}}`, not `{{nomfichier}}`)

## Language-Specific Notes

### Right-to-Left Languages

Currently, all supported EU languages use left-to-right text direction. If adding a RTL language in the future, additional CSS changes may be needed.

### Special Characters

Several EU languages use special characters that may require attention:

- **French**: é, è, ê, à, ç, œ
- **German**: ä, ö, ü, ß
- **Spanish**: ñ, á, é, í, ó, ú, ü
- **Portuguese**: ã, õ, ç, á, é, í, ó, ú
- **Polish**: ą, ć, ę, ł, ń, ó, ś, ź, ż
- **Czech**: č, ď, ě, ň, ř, š, ť, ů, ž
- **Greek**: α, β, γ, δ, ε, ζ, η, θ, etc.

All files should be saved with UTF-8 encoding to support these characters.

## Resources

- [react-i18next Documentation](https://react.i18next.com/)
- [i18next Documentation](https://www.i18next.com/)
- [ISO 639-1 Language Codes](https://en.wikipedia.org/wiki/List_of_ISO_639-1_codes)
- [EU Official Languages](https://european-union.europa.eu/principles-countries-history/languages_en)

## Getting Help

If you encounter issues with translations:

1. Check the browser console for i18next errors
2. Validate your JSON syntax using [JSONLint](https://jsonlint.com/)
3. Review the example translations in `en/translation.json`
4. Open an issue on the GitHub repository with details about the problem

## Contributing Translations

We welcome contributions for improving existing translations or completing placeholder translations:

1. Fork the repository
2. Create a new branch for your translation updates
3. Update the translation files
4. Test your changes locally
5. Submit a pull request with a clear description of your changes

Thank you for helping make this application accessible to users across Europe!
