# Multilingual Support Documentation

## Overview

The Foundry Meeting Audio Recording Processor now supports **24 European Union languages**, providing a fully internationalized user interface that adapts to the user's preferred language.

## Supported Languages

The application supports all official EU languages:

| Language | Code | Native Name |
|----------|------|-------------|
| Bulgarian | `bg` | Български |
| Czech | `cs` | Čeština |
| Danish | `da` | Dansk |
| German | `de` | Deutsch |
| Greek | `el` | Ελληνικά |
| English | `en` | English |
| Spanish | `es` | Español |
| Estonian | `et` | Eesti |
| Finnish | `fi` | Suomi |
| French | `fr` | Français |
| Irish | `ga` | Gaeilge |
| Croatian | `hr` | Hrvatski |
| Hungarian | `hu` | Magyar |
| Italian | `it` | Italiano |
| Lithuanian | `lt` | Lietuvių |
| Latvian | `lv` | Latviešu |
| Maltese | `mt` | Malti |
| Dutch | `nl` | Nederlands |
| Polish | `pl` | Polski |
| Portuguese | `pt` | Português |
| Romanian | `ro` | Română |
| Slovak | `sk` | Slovenčina |
| Slovenian | `sl` | Slovenščina |
| Swedish | `sv` | Svenska |

## Features

### 1. Language Selection

Users can switch between languages using the language selector dropdown located in the application header. The selected language is:
- **Persisted** in browser localStorage
- **Automatically detected** based on browser settings if no preference is saved
- **Fallback** to English if a translation is missing

### 2. Translated Content

All user-facing text is translatable, including:

- **Interface Elements**
  - Form labels and placeholders
  - Button text
  - Navigation items
  - Status messages

- **Tooltips and Help Text**
  - Detailed explanations for all features
  - Contextual help information
  - Accessibility labels

- **Error Messages**
  - Validation errors
  - Upload failures
  - Processing errors

- **Notifications**
  - Job started/completed/failed messages
  - Success confirmations
  - System alerts

- **Dynamic Content**
  - Progress indicators
  - Job status updates
  - Results metadata
  - NLP analysis sections

- **Additional Features**
  - Theme selector
  - Accessibility controls
  - Badge system
  - "Did You Know?" facts
  - Export options

### 3. Automatic Language Detection

The application uses `i18next-browser-languagedetector` to automatically detect the user's preferred language based on:
1. Previously saved language preference (localStorage)
2. Browser's language settings
3. HTML lang attribute

### 4. Fallback Mechanism

If a specific translation key is missing in the selected language:
1. The application falls back to the English translation
2. If no English translation exists, the key itself is displayed
3. Default values can be specified inline in components

## Technical Implementation

### Architecture

The multilingual support is implemented using:
- **i18next**: Core internationalization framework
- **react-i18next**: React bindings for i18next
- **i18next-http-backend**: Loads translations from JSON files
- **i18next-browser-languagedetector**: Automatic language detection

### File Structure

```
frontend/
├── public/
│   └── locales/          # Translation files
│       ├── en/
│       │   └── translation.json
│       ├── de/
│       │   └── translation.json
│       ├── fr/
│       │   └── translation.json
│       └── ... (24 languages total)
├── src/
│   ├── i18n.js           # i18next configuration
│   ├── LanguageSelector.js  # Language selection component
│   └── components/       # All components use useTranslation()
```

### Configuration

The i18n system is configured in `frontend/src/i18n.js`:

```javascript
i18n
  .use(HttpBackend)           // Load translations from public/locales
  .use(LanguageDetector)      // Detect user language
  .use(initReactI18next)      // Bind to React
  .init({
    fallbackLng: 'en',        // Default to English
    debug: false,
    interpolation: {
      escapeValue: false,     // React already escapes
    },
    backend: {
      loadPath: '/locales/{{lng}}/{{ns}}.json',
    },
    detection: {
      order: ['localStorage', 'navigator', 'htmlTag'],
      caches: ['localStorage'],
    },
    load: 'languageOnly',     // Handle language codes (e.g., en-US -> en)
  });
```

### Using Translations in Components

#### Basic Usage

```javascript
import { useTranslation } from 'react-i18next';

function MyComponent() {
  const { t } = useTranslation();
  
  return (
    <div>
      <h1>{t('app.title')}</h1>
      <button>{t('upload.uploadButton')}</button>
    </div>
  );
}
```

#### With Interpolation

```javascript
// Translation file: { "greeting": "Hello, {{name}}!" }
<p>{t('greeting', { name: 'John' })}</p>
// Output: Hello, John!
```

#### With Fallback

```javascript
<button>
  {t('badges.earned', { defaultValue: 'Badge Earned!' })}
</button>
```

#### With Count (Pluralization)

```javascript
// Translation file: 
// { "items_one": "{{count}} item", "items_other": "{{count}} items" }
<p>{t('items', { count: items.length })}</p>
```

## Translation File Structure

Each translation file (`frontend/public/locales/[lang]/translation.json`) contains a nested JSON structure:

```json
{
  "app": {
    "title": "Meeting Audio Transcription",
    "subtitle": "Upload audio files and transcribe..."
  },
  "upload": {
    "title": "Upload & Configure",
    "audioFile": "Audio File:",
    "uploadButton": "Transcribe"
  },
  "errors": {
    "noFile": "Please select an audio file",
    "uploadFailed": "Failed to submit transcription job"
  },
  ...
}
```

### Key Sections

1. **app**: Application title and branding
2. **upload**: File upload and configuration form
3. **tooltips**: Contextual help and explanations
4. **methods**: Transcription method names
5. **whisperModels**: Whisper model options
6. **jobs**: Job list and management
7. **status**: Job status labels
8. **results**: Transcription results display
9. **errors**: Error messages
10. **notifications**: Toast notifications
11. **export**: Export functionality
12. **audio**: Audio player controls
13. **accessibility**: Accessibility features
14. **languageSelector**: Language selector labels
15. **themes**: Theme selector
16. **didYouKnow**: Educational facts
17. **badges**: Achievement system

## Adding New Languages

To add support for a new language:

1. **Create language directory**
   ```bash
   mkdir -p frontend/public/locales/[language-code]
   ```

2. **Copy English template**
   ```bash
   cp frontend/public/locales/en/translation.json \
      frontend/public/locales/[language-code]/translation.json
   ```

3. **Translate the content**
   - Open the new `translation.json` file
   - Translate all values (keep keys unchanged)
   - Preserve placeholders like `{{filename}}`, `{{count}}`
   - Test with the application

4. **Add to language selector**
   - Edit `frontend/src/LanguageSelector.js`
   - Add the new language to the `languages` array:
   ```javascript
   { code: '[language-code]', name: '[Native Name]' }
   ```

5. **Test the integration**
   - Build the frontend: `npm run build`
   - Start the application
   - Select the new language from the dropdown
   - Verify all text is properly translated

## Adding New Translation Keys

When adding new features or text to the application:

1. **Add to English file first**
   ```json
   // frontend/public/locales/en/translation.json
   {
     "newFeature": {
       "title": "New Feature",
       "description": "Description of the new feature"
     }
   }
   ```

2. **Use in component**
   ```javascript
   const { t } = useTranslation();
   <h2>{t('newFeature.title')}</h2>
   <p>{t('newFeature.description')}</p>
   ```

3. **Add to all other language files**
   - Either translate immediately
   - Or use English as fallback (will work but not ideal)

4. **Use default values during development**
   ```javascript
   {t('newFeature.title', { defaultValue: 'New Feature' })}
   ```

## Best Practices

### For Developers

1. **Always use translation keys** - Never hardcode user-facing text
2. **Use semantic key names** - `upload.uploadButton` not `button1`
3. **Provide default values** - Helps during development
4. **Keep keys organized** - Group related translations
5. **Test with multiple languages** - Ensure UI doesn't break
6. **Consider text length** - Translations can be longer/shorter
7. **Use interpolation** - For dynamic content like `{{filename}}`
8. **Handle pluralization** - Different languages have different plural rules

### For Translators

1. **Preserve placeholders** - Keep `{{variable}}` unchanged
2. **Maintain formatting** - Preserve HTML tags if present
3. **Consider context** - Same word may need different translations in different contexts
4. **Test in application** - Verify translations fit in UI
5. **Keep tone consistent** - Match the formality of the original text
6. **Preserve meaning** - Don't translate word-for-word if it doesn't make sense
7. **Use native terminology** - For technical terms when appropriate

## Testing

### Manual Testing

1. **Switch languages**
   - Select each language from the dropdown
   - Verify all text updates immediately
   - Check that selection persists on page reload

2. **Test all features**
   - Upload form
   - Job list
   - Results display
   - Tooltips
   - Error messages
   - Notifications

3. **Check UI layout**
   - Longer translations (German, Dutch) shouldn't break layout
   - Shorter translations (Finnish) should still look good
   - Special characters display correctly

4. **Test fallbacks**
   - Temporarily remove a translation key
   - Verify English fallback appears
   - Restore the key

### Automated Testing

Add tests for internationalization:

```javascript
import { render } from '@testing-library/react';
import { I18nextProvider } from 'react-i18next';
import i18n from './i18n';

test('renders in German', () => {
  i18n.changeLanguage('de');
  const { getByText } = render(
    <I18nextProvider i18n={i18n}>
      <App />
    </I18nextProvider>
  );
  expect(getByText('Transkribieren')).toBeInTheDocument();
});
```

## Troubleshooting

### Language not changing

**Problem**: Selecting a language doesn't update the UI

**Solutions**:
- Clear browser localStorage: `localStorage.removeItem('i18nextLng')`
- Check browser console for errors
- Verify translation file exists at correct path
- Check network tab for 404 errors when loading translations

### Missing translations

**Problem**: Some text appears in English when other language selected

**Solutions**:
- Check translation file for the specific key
- Verify key path is correct (case-sensitive)
- Add missing translations or use fallback
- Check browser console for warnings

### UI layout broken

**Problem**: Text overflows or breaks layout in certain languages

**Solutions**:
- Use CSS `overflow-wrap: break-word` or `text-overflow: ellipsis`
- Increase container width or allow wrapping
- Use shorter translations if necessary
- Test with longest expected translations (German often longest)

### Translation not loading

**Problem**: Translation files return 404 errors

**Solutions**:
- Verify files are in `public/locales/[lang]/translation.json`
- Check that build includes the files
- Verify `loadPath` in i18n configuration
- Ensure proper case sensitivity in file names

## Performance Considerations

- **Lazy loading**: Translations are loaded on demand
- **Caching**: Loaded translations are cached in browser
- **File size**: Each language file is ~15-20KB (minimal impact)
- **Bundle size**: i18n libraries add ~50KB to bundle (gzipped)

## Future Enhancements

Potential improvements for the multilingual system:

1. **More languages**: Add non-EU languages (Japanese, Chinese, Arabic, etc.)
2. **Context-aware translations**: Different translations based on user context
3. **Right-to-left (RTL) support**: For Arabic, Hebrew, etc.
4. **Translation management**: Admin interface to manage translations
5. **Professional translations**: Replace placeholder translations with professional ones
6. **Date/time localization**: Format dates according to locale
7. **Number formatting**: Locale-specific number formats
8. **Currency support**: If billing features are added
9. **Keyboard shortcuts**: Language-specific shortcuts
10. **Voice language sync**: Auto-select transcription language based on UI language

## Resources

- **i18next Documentation**: https://www.i18next.com/
- **react-i18next Guide**: https://react.i18next.com/
- **Language Codes**: ISO 639-1 standard
- **Translation Services**: For professional translations
- **Unicode Character Table**: For special characters

## Support

For questions or issues related to multilingual support:
- Check this documentation
- Review i18next documentation
- Check GitHub issues
- Contact development team

---

**Last Updated**: February 2026  
**Version**: 1.0.0  
**Maintainer**: Development Team
