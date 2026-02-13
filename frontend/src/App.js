import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import './App.css';
import LanguageSelector from './LanguageSelector';

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

  const updateJobs = useCallback(async () => {
    const updatedJobs = await Promise.all(
      jobs.map(async (job) => {
        if (job.status === 'pending' || job.status === 'processing') {
          try {
            const response = await axios.get(`/api/jobs/${job.job_id}`);
            return response.data;
          } catch (error) {
            console.error('Error fetching job status:', error);
            return job;
          }
        }
        return job;
      })
    );
    setJobs(updatedJobs);
  }, [jobs]);

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

    try {
      const response = await axios.post('/api/transcribe', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      const newJob = {
        job_id: response.data.job_id,
        status: response.data.status,
        filename: file.name,
        method: method,
        created_at: new Date().toISOString(),
      };

      setJobs([newJob, ...jobs]);
      setFile(null);
      setTermsFile(null);
      setCustomTerms('');
      setLanguageCandidates('');
      document.getElementById('fileInput').value = '';
      if (document.getElementById('termsFileInput')) {
        document.getElementById('termsFileInput').value = '';
      }
    } catch (error) {
      setError(error.response?.data?.detail || t('errors.uploadFailed'));
    } finally {
      setLoading(false);
    }
  };

  const deleteJob = async (jobId) => {
    try {
      await axios.delete(`/api/jobs/${jobId}`);
      setJobs(jobs.filter(job => job.job_id !== jobId));
    } catch (error) {
      console.error('Error deleting job:', error);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <div className="header-content">
          <div className="header-text">
            <h1>{t('app.title')}</h1>
            <p>{t('app.subtitle')}</p>
          </div>
          <LanguageSelector />
        </div>
      </header>

      <div className="container">
        <div className="upload-section">
          <h2>{t('upload.title')}</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="fileInput">{t('upload.audioFile')}</label>
              <input
                id="fileInput"
                type="file"
                accept="audio/*"
                onChange={handleFileChange}
                className="file-input"
              />
              {file && <p className="file-info">{t('upload.fileSelected', { filename: file.name })}</p>}
            </div>

            <div className="form-group">
              <label htmlFor="method">{t('upload.method')}</label>
              <select
                id="method"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className="select-input"
              >
                <option value="azure">{t('methods.azure')}</option>
                <option value="whisper_local">{t('methods.whisper_local')}</option>
                <option value="whisper_api">{t('methods.whisper_api')}</option>
              </select>
            </div>

            {method === 'whisper_local' && (
              <div className="form-group">
                <label htmlFor="whisperModel">{t('upload.whisperModel')}</label>
                <select
                  id="whisperModel"
                  value={whisperModel}
                  onChange={(e) => setWhisperModel(e.target.value)}
                  className="select-input"
                >
                  <option value="tiny">{t('whisperModels.tiny')}</option>
                  <option value="base">{t('whisperModels.base')}</option>
                  <option value="small">{t('whisperModels.small')}</option>
                  <option value="medium">{t('whisperModels.medium')}</option>
                  <option value="large">{t('whisperModels.large')}</option>
                </select>
              </div>
            )}

            <div className="form-group">
              <label htmlFor="language">{t('upload.language')}</label>
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
              <label htmlFor="languageCandidates">{t('upload.languageCandidates')}</label>
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
              <label htmlFor="customTerms">{t('upload.customTerms')}</label>
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
              <label htmlFor="termsFileInput">{t('upload.termsFile')}</label>
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

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={enableDiarization}
                  onChange={(e) => setEnableDiarization(e.target.checked)}
                />
                {t('upload.enableDiarization')} {method !== 'azure' && t('upload.azureOnly')}
              </label>
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={enableNlp}
                  onChange={(e) => setEnableNlp(e.target.checked)}
                />
                {t('upload.enableNlp')}
              </label>
            </div>

            {error && <div className="error">{error}</div>}

            <button type="submit" disabled={loading || !file} className="submit-button">
              {loading ? t('upload.uploadingButton') : t('upload.uploadButton')}
            </button>
          </form>
        </div>

        <div className="jobs-section">
          <h2>{t('jobs.title')}</h2>
          {jobs.length === 0 ? (
            <p className="no-jobs">{t('jobs.noJobs')}</p>
          ) : (
            <div className="jobs-list">
              {jobs.map((job) => (
                <div key={job.job_id} className={`job-card ${job.status}`}>
                  <div className="job-header">
                    <h3>{job.filename}</h3>
                    <span className={`status-badge ${job.status}`}>
                      {t(`status.${job.status}`)}
                    </span>
                  </div>
                  <div className="job-info">
                    <p><strong>{t('jobs.method')}</strong> {job.method}</p>
                    <p><strong>{t('jobs.id')}</strong> {job.job_id}</p>
                    {job.progress && <p><strong>{t('jobs.progress')}</strong> {job.progress}</p>}
                    {job.error && <p className="error"><strong>{t('jobs.error')}</strong> {job.error}</p>}
                  </div>
                  
                  {job.status === 'completed' && job.result && (
                    <div className="results">
                      <h4>{t('results.title')}</h4>
                      <div className="transcription-text">
                        {job.result.transcription.full_text}
                      </div>
                      
                      {job.result.transcription.metadata && (
                        <div className="metadata">
                          <p><strong>{t('results.metadata.duration')}</strong> {job.result.transcription.duration.toFixed(2)}s</p>
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

                      {job.result.transcription.segments && (
                        <div className="segments">
                          <h4>{t('results.segments.title', { count: job.result.transcription.segments.length })}</h4>
                          <div className="segments-list">
                            {job.result.transcription.segments.slice(0, 5).map((segment, idx) => (
                              <div key={idx} className="segment">
                                <span className="timestamp">
                                  [{segment.start_time.toFixed(1)}s - {segment.end_time.toFixed(1)}s]
                                </span>
                                {segment.speaker_id && (
                                  <span className="speaker">{segment.speaker_id}:</span>
                                )}
                                <span className="text">{segment.text}</span>
                              </div>
                            ))}
                            {job.result.transcription.segments.length > 5 && (
                              <p className="more">{t('results.segments.more', { count: job.result.transcription.segments.length - 5 })}</p>
                            )}
                          </div>
                        </div>
                      )}

                      {job.result.nlp_analysis && (
                        <div className="nlp-results">
                          <h4>{t('results.nlp.title')}</h4>
                          {job.result.nlp_analysis.key_phrases && (
                            <div className="key-phrases">
                              <strong>{t('results.nlp.keyPhrases')}</strong>
                              <div className="tags">
                                {job.result.nlp_analysis.key_phrases.slice(0, 10).map((phrase, idx) => (
                                  <span key={idx} className="tag">{phrase.text}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {job.result.nlp_analysis.sentiment && (
                            <div className="sentiment">
                              <strong>{t('results.nlp.sentiment')}</strong> {job.result.nlp_analysis.sentiment.overall}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  
                  <button onClick={() => deleteJob(job.job_id)} className="delete-button">
                    {t('jobs.deleteButton')}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
