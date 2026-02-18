import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';
import './App.css';
import './accessibility.css';
import LanguageSelector from './LanguageSelector';
import ProgressBar from './components/ProgressBar';
import PipelineProgress from './components/PipelineProgress';
import TranscriptSearch from './components/TranscriptSearch';
import AudioPlayer from './components/AudioPlayer';
import ExportButton from './components/ExportButton';
import AccessibilityControls from './components/AccessibilityControls';
import ThemeSelector from './components/ThemeSelector';
import DidYouKnow from './components/DidYouKnow';
import BadgeSystem from './components/BadgeSystem';
import SpeakerAvatar from './components/SpeakerAvatar';
import InfoTooltip from './components/InfoTooltip';

function App() {
  const { t } = useTranslation();
  const [file, setFile] = useState(null);
  const [method, setMethod] = useState('azure');
  const [language, setLanguage] = useState('');
  const [enableDiarization, setEnableDiarization] = useState(true);
  const [whisperModel, setWhisperModel] = useState('base');
  const [enableNlp, setEnableNlp] = useState(true);
  const [customTerms, setCustomTerms] = useState('');
  const [termsFile, setTermsFile] = useState(null);
  const [languageCandidates, setLanguageCandidates] = useState('');
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);

  // Jobs sorted by creation date DESC (newest first)
  const sortedJobs = useMemo(() => {
    return [...jobs].sort((a, b) => {
      const dateA = a.created_at ? new Date(a.created_at).getTime() : 0;
      const dateB = b.created_at ? new Date(b.created_at).getTime() : 0;
      return dateB - dateA;
    });
  }, [jobs]);

  // Advanced settings state
  // Azure Speech advanced
  const [profanityFilter, setProfanityFilter] = useState('masked');
  const [maxSpeakers, setMaxSpeakers] = useState(10);
  const [wordLevelTimestamps, setWordLevelTimestamps] = useState(false);
  // Whisper advanced
  const [whisperTemperature, setWhisperTemperature] = useState(0);
  const [whisperPrompt, setWhisperPrompt] = useState('');
  // Audio pre-processing
  const [audioChannels, setAudioChannels] = useState(1);
  const [audioSampleRate, setAudioSampleRate] = useState(16000);
  const [audioBitRate, setAudioBitRate] = useState('16k');
  // NLP advanced
  const [summarySentenceCount, setSummarySentenceCount] = useState(6);
  const [nlpKeyPhrases, setNlpKeyPhrases] = useState(true);
  const [nlpEntities, setNlpEntities] = useState(true);
  const [nlpActionItems, setNlpActionItems] = useState(true);
  const [nlpSummary, setNlpSummary] = useState(true);
  const [nlpSegmentSentiment, setNlpSegmentSentiment] = useState(true);
  const [sentimentThreshold, setSentimentThreshold] = useState(0.6);
  // Load existing jobs from backend on mount
  useEffect(() => {
    const loadJobs = async () => {
      try {
        const response = await axios.get('/api/jobs');
        if (response.data?.jobs?.length > 0) {
          // Fetch full details for each job
          const fullJobs = await Promise.all(
            response.data.jobs.map(async (j) => {
              try {
                const detail = await axios.get(`/api/jobs/${j.job_id}`);
                return { ...j, ...detail.data };
              } catch {
                return j;
              }
            })
          );
          setJobs(fullJobs);
        }
      } catch (err) {
        console.error('Failed to load existing jobs:', err);
      }
    };
    loadJobs();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const updateJobs = useCallback(async () => {
    const updatedJobs = await Promise.all(
      jobs.map(async (job) => {
        // Skip uploading jobs – they don't exist on the server yet
        if (job.status === 'uploading') return job;
        if (job.status === 'pending' || job.status === 'processing') {
          try {
            const response = await axios.get(`/api/jobs/${job.job_id}`);
            const updatedJob = { ...job, ...response.data };
            
            // Notify user when job completes
            if (updatedJob.status === 'completed' && job.status !== 'completed') {
              toast.success(t('notifications.jobCompleted', { 
                defaultValue: `Transcription completed: ${job.filename}`,
                filename: job.filename 
              }));
            } else if (updatedJob.status === 'failed' && job.status !== 'failed') {
              toast.error(t('notifications.jobFailed', { 
                defaultValue: `Transcription failed: ${job.filename}`,
                filename: job.filename 
              }));
            }
            
            return updatedJob;
          } catch (error) {
            console.error('Error fetching job status:', error);
            return job;
          }
        }
        return job;
      })
    );
    setJobs(updatedJobs);
  }, [jobs, t]);

  // Poll for job updates
  useEffect(() => {
    const interval = setInterval(() => {
      if (jobs.length > 0) {
        updateJobs();
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [jobs, updateJobs]);

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError('');
  };

  const handleTermsFileChange = (e) => {
    setTermsFile(e.target.files[0]);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError(t('errors.noFile'));
      return;
    }

    setLoading(true);
    setError('');
    setUploadProgress(0);

    // Create an immediate "uploading" job for instant UI feedback
    const tempId = `uploading-${Date.now()}`;
    const uploadingJob = {
      job_id: tempId,
      status: 'uploading',
      filename: file.name,
      method: method,
      created_at: new Date().toISOString(),
      uploadProgress: 0,
    };
    setJobs(prev => [uploadingJob, ...prev]);

    const formData = new FormData();
    formData.append('file', file);
    formData.append('method', method);
    if (language) formData.append('language', language);
    formData.append('enable_diarization', enableDiarization);
    formData.append('whisper_model', whisperModel);
    formData.append('enable_nlp', enableNlp);
    if (customTerms) formData.append('custom_terms', customTerms);
    if (termsFile) formData.append('terms_file', termsFile);
    if (languageCandidates) formData.append('language_candidates', languageCandidates);

    // Audio pre-processing settings
    formData.append('audio_channels', audioChannels);
    formData.append('audio_sample_rate', audioSampleRate);
    formData.append('audio_bit_rate', audioBitRate);

    // Advanced settings
    if (method === 'azure') {
      formData.append('profanity_filter', profanityFilter);
      formData.append('max_speakers', maxSpeakers);
      formData.append('word_level_timestamps', wordLevelTimestamps);
    }
    if (method === 'whisper_api') {
      if (whisperTemperature > 0) formData.append('whisper_temperature', whisperTemperature);
      if (whisperPrompt) formData.append('whisper_prompt', whisperPrompt);
    }
    if (enableNlp) {
      formData.append('summary_sentence_count', summarySentenceCount);
      const features = [];
      if (nlpKeyPhrases) features.push('key_phrases');
      if (nlpEntities) features.push('entities');
      if (nlpActionItems) features.push('action_items');
      if (nlpSummary) features.push('summary');
      if (nlpSegmentSentiment) features.push('segment_sentiment');
      formData.append('nlp_features', features.join(','));
      if (nlpSegmentSentiment) formData.append('sentiment_confidence_threshold', sentimentThreshold);
    }

    try {
      const response = await axios.post('/api/transcribe', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(pct);
          // Update the uploading job's progress
          setJobs(prev => prev.map(j =>
            j.job_id === tempId ? { ...j, uploadProgress: pct } : j
          ));
        },
      });

      // Replace the uploading placeholder with the real job
      const newJob = {
        job_id: response.data.job_id,
        status: response.data.status,
        filename: file.name,
        method: method,
        created_at: new Date().toISOString(),
      };

      setJobs(prev => prev.map(j => j.job_id === tempId ? newJob : j));
      setFile(null);
      setTermsFile(null);
      setCustomTerms('');
      setLanguageCandidates('');
      setUploadProgress(0);
      document.getElementById('fileInput').value = '';
      if (document.getElementById('termsFileInput')) {
        document.getElementById('termsFileInput').value = '';
      }
      
      // Show success notification
      toast.info(t('notifications.jobStarted', { 
        defaultValue: 'Transcription started',
      }));
    } catch (error) {
      // Remove the uploading placeholder on error
      setJobs(prev => prev.filter(j => j.job_id !== tempId));
      const errorMsg = error.response?.data?.detail || t('errors.uploadFailed');
      setError(errorMsg);
      toast.error(errorMsg);
    } finally {
      setLoading(false);
      setUploadProgress(0);
    }
  };

  const deleteJob = async (jobId) => {
    try {
      await axios.delete(`/api/jobs/${jobId}`);
      setJobs(jobs.filter(job => job.job_id !== jobId));
      toast.success(t('notifications.jobDeleted', { defaultValue: 'Job deleted successfully' }));
    } catch (error) {
      console.error('Error deleting job:', error);
      toast.error(t('notifications.jobDeleteFailed', { defaultValue: 'Failed to delete job' }));
    }
  };

  return (
    <div className="App">
      {/* Skip to content link for keyboard navigation */}
      <a href="#main-content" className="skip-to-content">
        {t('accessibility.skipToContent', { defaultValue: 'Skip to main content' })}
      </a>
      
      {/* Theme Selector */}
      <ThemeSelector />
      
      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        role="alert"
        aria-live="polite"
      />
      <header className="App-header" role="banner">
        <div className="header-content">
          <BadgeSystem jobs={jobs} />
          <div className="header-text">
            <h1>{t('app.title')}</h1>
            <p>{t('app.subtitle')}</p>
          </div>
          <LanguageSelector />
        </div>
      </header>

      {/* Subtle tip bar */}
      <DidYouKnow />

      <main id="main-content" className="container" role="main">
        <section className="upload-section" aria-labelledby="upload-heading">
          <h2 id="upload-heading">{t('upload.title')}</h2>
          <form onSubmit={handleSubmit} aria-label={t('upload.formLabel', { defaultValue: 'Transcription configuration form' })}>
            <div className="form-group">
              <label htmlFor="fileInput">{t('upload.audioFile')}<InfoTooltip text={t('tooltips.audioFile')} /></label>
              <input
                id="fileInput"
                type="file"
                accept="audio/*"
                onChange={handleFileChange}
                className="file-input"
                aria-required="true"
                aria-describedby={file ? "file-selected-info" : undefined}
              />
              {file && <p id="file-selected-info" className="file-info">{t('upload.fileSelected', { filename: file.name })}</p>}
            </div>

            <div className="form-group">
              <label htmlFor="method">{t('upload.method')}<InfoTooltip text={t('tooltips.method')} /></label>
              <select
                id="method"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className="select-input"
              >
                <option value="azure">{t('methods.azure')}</option>
                <option value="whisper_api">{t('methods.whisper_api', { defaultValue: 'Azure Whisper' })}</option>
              </select>
            </div>

            {/* Method-specific settings inline */}
            <div className="settings-section method-settings">
              <h4 className="settings-section-title">
                {method === 'azure' ? t('upload.azureSectionTitle') : t('upload.whisperSectionTitle')}
              </h4>

              {method === 'azure' && (
                <>
                  <div className="form-group">
                    <label htmlFor="languageCandidates">{t('upload.languageCandidates')}<InfoTooltip text={t('tooltips.languageCandidates')} /></label>
                    <input
                      id="languageCandidates"
                      type="text"
                      value={languageCandidates}
                      onChange={(e) => setLanguageCandidates(e.target.value)}
                      placeholder={t('upload.languageCandidatesPlaceholder')}
                      className="text-input"
                    />
                    <small className="help-text">
                      {t('upload.languageCandidatesHelp')}
                    </small>
                  </div>

                  <div className="form-group">
                    <label htmlFor="profanityFilter">{t('upload.profanityFilter')}<InfoTooltip text={t('tooltips.profanityFilter')} /></label>
                    <select
                      id="profanityFilter"
                      value={profanityFilter}
                      onChange={(e) => setProfanityFilter(e.target.value)}
                      className="select-input"
                    >
                      <option value="masked">{t('upload.profanityMasked')}</option>
                      <option value="removed">{t('upload.profanityRemoved')}</option>
                      <option value="raw">{t('upload.profanityRaw')}</option>
                    </select>
                  </div>

                  <div className="form-group">
                    <label htmlFor="maxSpeakers">{t('upload.maxSpeakers')}<InfoTooltip text={t('tooltips.maxSpeakers')} /></label>
                    <input
                      id="maxSpeakers"
                      type="number"
                      min="1"
                      max="36"
                      value={maxSpeakers}
                      onChange={(e) => setMaxSpeakers(parseInt(e.target.value) || 10)}
                      className="text-input number-input"
                    />
                    <small className="help-text">{t('upload.maxSpeakersHelp')}</small>
                  </div>

                  <div className="form-group checkbox-group">
                    <label>
                      <input
                        type="checkbox"
                        checked={wordLevelTimestamps}
                        onChange={(e) => setWordLevelTimestamps(e.target.checked)}
                      />
                      {t('upload.wordLevelTimestamps')}<InfoTooltip text={t('tooltips.wordLevelTimestamps')} />
                    </label>
                  </div>
                </>
              )}

              {method === 'whisper_api' && (
                <>
                  <div className="form-group">
                    <label htmlFor="whisperTemperature">{t('upload.temperature')}<InfoTooltip text={t('tooltips.temperature')} /></label>
                    <div className="range-with-value">
                      <input
                        id="whisperTemperature"
                        type="range"
                        min="0"
                        max="1"
                        step="0.1"
                        value={whisperTemperature}
                        onChange={(e) => setWhisperTemperature(parseFloat(e.target.value))}
                        className="range-input"
                      />
                      <span className="range-value">{whisperTemperature.toFixed(1)}</span>
                    </div>
                    <small className="help-text">
                      {t('upload.temperatureHelp')}
                    </small>
                  </div>

                  <div className="form-group">
                    <label htmlFor="whisperPrompt">{t('upload.initialPrompt')}<InfoTooltip text={t('tooltips.initialPrompt')} /></label>
                    <textarea
                      id="whisperPrompt"
                      value={whisperPrompt}
                      onChange={(e) => {
                        if (e.target.value.length <= 800) setWhisperPrompt(e.target.value);
                      }}
                      placeholder={t('upload.initialPromptPlaceholder')}
                      className={`text-input${whisperPrompt.length >= 800 ? ' input-limit-reached' : ''}`}
                      rows="3"
                      maxLength={800}
                    />
                    <small className="help-text">
                      {t('upload.initialPromptHelp', { count: whisperPrompt.length })}
                    </small>
                  </div>
                </>
              )}
            </div>

            <div className="form-group">
              <label htmlFor="language">{t('upload.language')}<InfoTooltip text={t('tooltips.language')} /></label>
              <input
                id="language"
                type="text"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                placeholder={t('upload.languagePlaceholder')}
                className="text-input"
              />
            </div>

            <div className="form-group">
              <label htmlFor="customTerms">{t('upload.customTerms')}<InfoTooltip text={t('tooltips.customTerms')} /></label>
              <textarea
                id="customTerms"
                value={customTerms}
                onChange={(e) => setCustomTerms(e.target.value)}
                placeholder={t('upload.customTermsPlaceholder')}
                className="text-input"
                rows="4"
              />
              <small className="help-text">
                {t('upload.customTermsHelp')}
              </small>
            </div>

            <div className="form-group">
              <label htmlFor="termsFileInput">{t('upload.termsFile')}<InfoTooltip text={t('tooltips.termsFile')} /></label>
              <input
                id="termsFileInput"
                type="file"
                accept=".txt,.csv"
                onChange={handleTermsFileChange}
                className="file-input"
              />
              {termsFile && <p className="file-info">{t('upload.termsFileSelected', { filename: termsFile.name })}</p>}
              <small className="help-text">
                {t('upload.termsFileHelp')}
              </small>
            </div>

            {/* Audio Pre-processing Settings */}
            <div className="settings-section preprocessing-settings">
              <h4 className="settings-section-title">{t('upload.preprocessingSectionTitle', { defaultValue: '🔊 Audio Pre-processing' })}</h4>

              <div className="form-group">
                <label htmlFor="audioChannels">{t('upload.audioChannels', { defaultValue: 'Channels' })}<InfoTooltip text={t('tooltips.audioChannels', { defaultValue: 'Number of audio channels. Use 1 (mono) for best speech recognition results. Use 2 (stereo) only if your recording has separate speaker channels.' })} /></label>
                <select
                  id="audioChannels"
                  value={audioChannels}
                  onChange={(e) => setAudioChannels(parseInt(e.target.value))}
                  className="select-input"
                >
                  <option value={1}>{t('upload.channelsMono', { defaultValue: '1 – Mono (recommended)' })}</option>
                  <option value={2}>{t('upload.channelsStereo', { defaultValue: '2 – Stereo' })}</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="audioSampleRate">{t('upload.audioSampleRate', { defaultValue: 'Sample Rate' })}<InfoTooltip text={t('tooltips.audioSampleRate', { defaultValue: 'Audio sample rate in Hz. 16 kHz is optimal for speech recognition. Higher rates preserve more audio detail but increase processing time and file size.' })} /></label>
                <select
                  id="audioSampleRate"
                  value={audioSampleRate}
                  onChange={(e) => setAudioSampleRate(parseInt(e.target.value))}
                  className="select-input"
                >
                  <option value={8000}>8,000 Hz (telephone quality)</option>
                  <option value={16000}>16,000 Hz (recommended)</option>
                  <option value={22050}>22,050 Hz</option>
                  <option value={44100}>44,100 Hz (CD quality)</option>
                  <option value={48000}>48,000 Hz (studio quality)</option>
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="audioBitRate">{t('upload.audioBitRate', { defaultValue: 'Bit Rate' })}<InfoTooltip text={t('tooltips.audioBitRate', { defaultValue: 'Audio encoding bit rate. Lower values reduce file size, higher values preserve quality. 16k is sufficient for speech; use higher for music or high-fidelity recordings.' })} /></label>
                <select
                  id="audioBitRate"
                  value={audioBitRate}
                  onChange={(e) => setAudioBitRate(e.target.value)}
                  className="select-input"
                >
                  <option value="16k">16 kbps (speech optimised)</option>
                  <option value="32k">32 kbps</option>
                  <option value="64k">64 kbps</option>
                  <option value="128k">128 kbps (high quality)</option>
                  <option value="192k">192 kbps</option>
                  <option value="256k">256 kbps (studio quality)</option>
                </select>
              </div>
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={enableDiarization}
                  onChange={(e) => setEnableDiarization(e.target.checked)}
                />
                {t('upload.enableDiarization')}<InfoTooltip text={t('tooltips.enableDiarization')} />
              </label>
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={enableNlp}
                  onChange={(e) => setEnableNlp(e.target.checked)}
                />
                {t('upload.enableNlp')}<InfoTooltip text={t('tooltips.enableNlp')} />
              </label>
            </div>

            {/* NLP Settings inline – visible when NLP is enabled */}
            {enableNlp && (
              <div className="settings-section nlp-settings">
                <h4 className="settings-section-title">{t('upload.nlpSectionTitle')}</h4>

                <div className="form-group">
                  <label htmlFor="summarySentenceCount">{t('upload.summaryLength')}<InfoTooltip text={t('tooltips.summaryLength')} /></label>
                  <div className="range-with-value">
                    <input
                      id="summarySentenceCount"
                      type="range"
                      min="2"
                      max="15"
                      step="1"
                      value={summarySentenceCount}
                      onChange={(e) => setSummarySentenceCount(parseInt(e.target.value))}
                      className="range-input"
                    />
                    <span className="range-value">{t('upload.summaryLengthValue', { count: summarySentenceCount })}</span>
                  </div>
                </div>

                <div className="nlp-feature-toggles">
                  <label className="feature-toggle">
                    <input type="checkbox" checked={nlpSegmentSentiment} onChange={(e) => setNlpSegmentSentiment(e.target.checked)} />
                    <span className="toggle-label">{t('upload.nlpSegmentSentiment')}</span>
                    <InfoTooltip text={t('tooltips.nlpSegmentSentiment')} />
                  </label>
                  {nlpSegmentSentiment && (
                    <div className="form-group sentiment-threshold-group">
                      <label htmlFor="sentimentThreshold">{t('upload.sentimentThreshold', { defaultValue: 'Sentiment Confidence Threshold' })}<InfoTooltip text={t('tooltips.sentimentThreshold', { defaultValue: 'Minimum confidence score required to label a segment as positive or negative. Segments below this threshold are marked as neutral. Higher values = only strong sentiments shown.' })} /></label>
                      <div className="range-with-value">
                        <input
                          id="sentimentThreshold"
                          type="range"
                          min="0.1"
                          max="0.95"
                          step="0.05"
                          value={sentimentThreshold}
                          onChange={(e) => setSentimentThreshold(parseFloat(e.target.value))}
                          className="range-input"
                        />
                        <span className="range-value">{(sentimentThreshold * 100).toFixed(0)}%</span>
                      </div>
                      <small className="help-text">{t('upload.sentimentThresholdHelp', { defaultValue: 'Default: 60%. Higher = only strong emotions shown, lower = more sensitive.' })}</small>
                    </div>
                  )}
                  <label className="feature-toggle">
                    <input type="checkbox" checked={nlpKeyPhrases} onChange={(e) => setNlpKeyPhrases(e.target.checked)} />
                    <span className="toggle-label">{t('upload.nlpKeyPhrases')}</span>
                    <InfoTooltip text={t('tooltips.nlpKeyPhrases')} />
                  </label>
                  <label className="feature-toggle">
                    <input type="checkbox" checked={nlpEntities} onChange={(e) => setNlpEntities(e.target.checked)} />
                    <span className="toggle-label">{t('upload.nlpEntities')}</span>
                    <InfoTooltip text={t('tooltips.nlpEntities')} />
                  </label>
                  <label className="feature-toggle">
                    <input type="checkbox" checked={nlpActionItems} onChange={(e) => setNlpActionItems(e.target.checked)} />
                    <span className="toggle-label">{t('upload.nlpActionItems')}</span>
                    <InfoTooltip text={t('tooltips.nlpActionItems')} />
                  </label>
                  <label className="feature-toggle">
                    <input type="checkbox" checked={nlpSummary} onChange={(e) => setNlpSummary(e.target.checked)} />
                    <span className="toggle-label">{t('upload.nlpSummary')}</span>
                    <InfoTooltip text={t('tooltips.nlpSummary')} />
                  </label>
                </div>
              </div>
            )}

            {error && <div className="error" role="alert" aria-live="assertive">{error}</div>}

            <button 
              type="submit" 
              disabled={loading || !file} 
              className="submit-button"
              aria-label={loading ? t('upload.uploadingButton') : t('upload.uploadButton')}
            >
              {loading ? t('upload.uploadingButton') : t('upload.uploadButton')}
            </button>
          </form>
        </section>

        <section className="jobs-section" aria-labelledby="jobs-heading">
          <h2 id="jobs-heading">{t('jobs.title')}</h2>
          {sortedJobs.length === 0 ? (
            <p className="no-jobs">{t('jobs.noJobs')}</p>
          ) : (
            <div className="jobs-list" role="list">
              {sortedJobs.map((job) => (
                <JobCard key={job.job_id} job={job} deleteJob={deleteJob} t={t} />
              ))}
            </div>
          )}
        </section>
      </main>
      
      {/* Accessibility Controls */}
      <AccessibilityControls />
    </div>
  );
}

export default App;

/* ------------------------------------------------------------------ */
/* Speaker-colour helper (matches AudioPlayer & SpeakerAvatar palette) */
/* ------------------------------------------------------------------ */
const SPEAKER_COLORS = [
  '#667eea', '#764ba2', '#f39c12', '#2ecc71', '#e74c3c',
  '#3498db', '#9b59b6', '#1abc9c', '#e67e22', '#34495e',
  '#16a085', '#c0392b',
];
function speakerColor(id) {
  if (!id) return SPEAKER_COLORS[0];
  const n = parseInt(id.match(/\d+/)?.[0] || '0', 10);
  return SPEAKER_COLORS[n % SPEAKER_COLORS.length];
}

/* ------------------------------------------------------------------ */
/* Group consecutive segments by speaker into "turns"                  */
/* ------------------------------------------------------------------ */
function groupBySpeaker(segments) {
  if (!segments || segments.length === 0) return [];
  const turns = [];
  let current = null;

  for (const seg of segments) {
    const speaker = seg.speaker_id || 'Unknown';
    if (!current || current.speaker !== speaker) {
      current = {
        speaker,
        startTime: seg.start_time,
        endTime: seg.end_time,
        parts: [seg],
      };
      turns.push(current);
    } else {
      current.endTime = seg.end_time;
      current.parts.push(seg);
    }
  }
  return turns;
}

function formatTimestamp(seconds) {
  if (!seconds || isNaN(seconds)) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

/* ------------------------------------------------------------------ */
/* JobCard – each job gets its own audio ref + currentTime state       */
/* ------------------------------------------------------------------ */
function JobCard({ job, deleteJob, t }) {
  const audioPlayerRef = useRef(null);
  const [currentTime, setCurrentTime] = useState(0);
  const transcriptRef = useRef(null);

  // Auto-scroll transcript to active segment (fine-grained, line-by-line)
  useEffect(() => {
    const container = transcriptRef.current;
    if (!container) return;
    const active = container.querySelector('.segment-line.active');
    if (active) {
      const cTop = container.scrollTop;
      const cHeight = container.clientHeight;
      const eTop = active.offsetTop - container.offsetTop;
      const eHeight = active.offsetHeight;
      // Only scroll if the active segment is outside the visible area
      if (eTop < cTop) {
        container.scrollTop = eTop;
      } else if (eTop + eHeight > cTop + cHeight) {
        container.scrollTop = eTop + eHeight - cHeight;
      }
    }
  }, [currentTime]);

  const handleSeekTo = (time) => {
    if (audioPlayerRef.current) {
      audioPlayerRef.current.seekTo(time);
    }
  };

  const METHOD_LABELS = {
    azure: 'Azure AI Speech',
    whisper_api: 'Azure OpenAI Whisper',
    whisper_local: 'OpenAI Whisper (Local)',
  };

  const segments = job.result?.transcription?.segments;
  const turns = segments ? groupBySpeaker(segments) : [];
  const segmentSentiments = job.result?.nlp_analysis?.segment_sentiments;

  return (
    <article className={`job-card ${job.status}`} role="listitem">
      <div className="job-header">
        <h3>{job.filename}</h3>
        <span className={`status-badge ${job.status}`} role="status" aria-label={t(`status.${job.status}`)}>
          {job.status === 'uploading'
            ? `Uploading ${job.uploadProgress || 0}%`
            : t(`status.${job.status}`)}
        </span>
      </div>

      {/* Upload progress bar */}
      {job.status === 'uploading' && (
        <div className="upload-progress-bar">
          <div className="upload-progress-fill" style={{ width: `${job.uploadProgress || 0}%` }} />
        </div>
      )}
      <div className="job-info">
        <p><strong>{t('jobs.method')}</strong> {METHOD_LABELS[job.method] || job.method}</p>
        <p><strong>{t('jobs.id')}</strong> {job.job_id}</p>
        {job.error && <p className="error"><strong>{t('jobs.error')}</strong> {job.error}</p>}
      </div>

      {/* Progress bar for pending/processing jobs */}
      {(job.status === 'pending' || job.status === 'processing') && (
        job.pipeline_stages
          ? <PipelineProgress
              stages={job.pipeline_stages}
              progress={job.progress}
              status={job.status}
              startedAt={job.started_at}
            />
          : <ProgressBar progress={job.progress} status={job.status} startedAt={job.started_at} />
      )}

      {job.status === 'completed' && job.result && (
        <div className="results">
          {/* Export button */}
          <div className="results-header">
            <h4>{t('results.title')}</h4>
            <ExportButton
              jobId={job.job_id}
              transcription={job.result.transcription}
              nlpAnalysis={job.result.nlp_analysis}
              filename={job.filename}
            />
          </div>

          {/* Audio Player */}
          <AudioPlayer
            ref={audioPlayerRef}
            jobId={job.job_id}
            segments={segments}
            onTimeUpdate={setCurrentTime}
            segmentSentiments={segmentSentiments}
          />

          {/* Transcript Search */}
          <TranscriptSearch
            transcript={job.result.transcription.full_text}
            segments={segments}
          />

          {/* ---- Speaker-segmented transcript ---- */}
          {turns.length > 0 ? (
            <div className="transcript-by-speaker" ref={transcriptRef}>
              {turns.map((turn, idx) => {
                const isActive =
                  currentTime >= turn.startTime && currentTime < turn.endTime;
                return (
                  <div
                    key={idx}
                    className={`transcript-turn ${isActive ? 'active' : ''}`}
                    onClick={() => handleSeekTo(turn.startTime)}
                  >
                    <div className="turn-header">
                      <SpeakerAvatar speakerId={turn.speaker} size="small" />
                      <span className="turn-speaker" style={{ color: speakerColor(turn.speaker) }}>
                        {turn.speaker}
                      </span>
                      <span className="turn-time">
                        {formatTimestamp(turn.startTime)} – {formatTimestamp(turn.endTime)}
                      </span>
                    </div>
                    <div className="turn-text">
                      {turn.parts.map((seg, si) => {
                        const segActive =
                          currentTime >= seg.start_time && currentTime < seg.end_time;
                        return (
                          <span
                            key={si}
                            className={`segment-line${segActive ? ' active' : ''}`}
                            onClick={(e) => { e.stopPropagation(); handleSeekTo(seg.start_time); }}
                          >
                            {si > 0 && ' '}
                            {seg.text}
                          </span>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
            </div>
          ) : (
            <div className="transcription-text">
              {job.result.transcription.full_text}
            </div>
          )}

          {/* Metadata */}
          {job.result.transcription.metadata && (
            <div className="metadata">
              <p><strong>{t('results.metadata.duration')}</strong> {job.result.transcription.duration?.toFixed(2)}s</p>
              <p><strong>{t('results.metadata.language')}</strong> {job.result.transcription.language}</p>
              {job.result.transcription.metadata.speaker_count && (
                <p><strong>{t('results.metadata.speakers')}</strong> {job.result.transcription.metadata.speaker_count}</p>
              )}
              {job.result.transcription.metadata.custom_terms_count > 0 && (
                <p><strong>{t('results.metadata.customTerms')}</strong> {job.result.transcription.metadata.custom_terms_count}</p>
              )}
              {job.result.transcription.metadata.language_candidates &&
               job.result.transcription.metadata.language_candidates.length > 0 && (
                <p><strong>{t('results.metadata.multiLanguage')}</strong> {job.result.transcription.metadata.language_candidates.join(', ')}</p>
              )}
            </div>
          )}

          {/* NLP analysis */}
          {job.result.nlp_analysis && (
            <div className="nlp-results">
              <h4>{t('results.nlp.title')}</h4>

              {/* Summary */}
              {job.result.nlp_analysis.summary_text && (
                <div className="nlp-section nlp-summary">
                  <h5>{t('results.nlp.summary')}</h5>
                  <p>{job.result.nlp_analysis.summary_text}</p>
                </div>
              )}

              {/* Action Items */}
              <div className="nlp-section nlp-action-items">
                <h5>{t('results.nlp.actionItems')}</h5>
                {job.result.nlp_analysis.action_items && job.result.nlp_analysis.action_items.length > 0 ? (
                  <ul>
                    {job.result.nlp_analysis.action_items.map((item, idx) => (
                      <li key={idx}>
                        <span className="action-text">{item.text}</span>
                        {item.assignee && <span className="action-assignee">@{item.assignee}</span>}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="nlp-empty">{t('results.nlp.noActionItems')}</p>
                )}
              </div>

              {/* Key Phrases */}
              <div className="nlp-section nlp-key-phrases">
                <h5>{t('results.nlp.keyPhrases')}</h5>
                {job.result.nlp_analysis.key_phrases && job.result.nlp_analysis.key_phrases.length > 0 ? (
                  <div className="tags">
                    {job.result.nlp_analysis.key_phrases.slice(0, 15).map((phrase, idx) => (
                      <span key={idx} className="tag">{phrase.text}</span>
                    ))}
                  </div>
                ) : (
                  <p className="nlp-empty">{t('results.nlp.noKeyPhrases')}</p>
                )}
              </div>

              {/* Topics */}
              {job.result.nlp_analysis.topics && job.result.nlp_analysis.topics.length > 0 && (
                <div className="nlp-section nlp-topics">
                  <h5>{t('results.nlp.topics')}</h5>
                  <div className="tags">
                    {job.result.nlp_analysis.topics.map((topic, idx) => (
                      <span key={idx} className="tag tag-topic">{topic}</span>
                    ))}
                  </div>
                </div>
              )}

              {/* Entities */}
              {job.result.nlp_analysis.entities && job.result.nlp_analysis.entities.length > 0 && (
                <div className="nlp-section nlp-entities">
                  <h5>{t('results.nlp.entities')}</h5>
                  <div className="entity-list">
                    {job.result.nlp_analysis.entities.slice(0, 15).map((entity, idx) => (
                      <span key={idx} className="entity-chip" title={`${entity.category}${entity.subcategory ? ' / ' + entity.subcategory : ''} (${(entity.confidence * 100).toFixed(0)}%)`}>
                        <span className="entity-category-dot" data-category={entity.category} />
                        {entity.text}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <button onClick={() => deleteJob(job.job_id)} className="delete-button">
        {t('jobs.deleteButton')}
      </button>
    </article>
  );
}
