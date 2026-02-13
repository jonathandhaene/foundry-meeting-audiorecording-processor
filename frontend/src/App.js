import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './App.css';

function App() {
  const [file, setFile] = useState(null);
  const [method, setMethod] = useState('azure');
  const [language, setLanguage] = useState('');
  const [enableDiarization, setEnableDiarization] = useState(true);
  const [whisperModel, setWhisperModel] = useState('base');
  const [enableNlp, setEnableNlp] = useState(true);
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Poll for job updates
  useEffect(() => {
    const interval = setInterval(() => {
      if (jobs.length > 0) {
        updateJobs();
      }
    }, 2000);
    return () => clearInterval(interval);
  }, [jobs]);

  const updateJobs = async () => {
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
  };

  const handleFileChange = (e) => {
    setFile(e.target.files[0]);
    setError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select an audio file');
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
      document.getElementById('fileInput').value = '';
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to submit transcription job');
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
        <h1>Meeting Audio Transcription</h1>
        <p>Upload audio files and transcribe using Azure Speech or Whisper</p>
      </header>

      <div className="container">
        <div className="upload-section">
          <h2>Upload & Configure</h2>
          <form onSubmit={handleSubmit}>
            <div className="form-group">
              <label htmlFor="fileInput">Audio File:</label>
              <input
                id="fileInput"
                type="file"
                accept="audio/*"
                onChange={handleFileChange}
                className="file-input"
              />
              {file && <p className="file-info">Selected: {file.name}</p>}
            </div>

            <div className="form-group">
              <label htmlFor="method">Transcription Method:</label>
              <select
                id="method"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
                className="select-input"
              >
                <option value="azure">Azure Speech Services</option>
                <option value="whisper_local">Whisper (Local)</option>
                <option value="whisper_api">Whisper (OpenAI API)</option>
              </select>
            </div>

            {method === 'whisper_local' && (
              <div className="form-group">
                <label htmlFor="whisperModel">Whisper Model:</label>
                <select
                  id="whisperModel"
                  value={whisperModel}
                  onChange={(e) => setWhisperModel(e.target.value)}
                  className="select-input"
                >
                  <option value="tiny">Tiny (fastest, least accurate)</option>
                  <option value="base">Base</option>
                  <option value="small">Small</option>
                  <option value="medium">Medium</option>
                  <option value="large">Large (slowest, most accurate)</option>
                </select>
              </div>
            )}

            <div className="form-group">
              <label htmlFor="language">Language (optional):</label>
              <input
                id="language"
                type="text"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
                placeholder="e.g., en-US, es-ES (leave empty for auto-detect)"
                className="text-input"
              />
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={enableDiarization}
                  onChange={(e) => setEnableDiarization(e.target.checked)}
                />
                Enable Speaker Diarization {method !== 'azure' && '(Azure only)'}
              </label>
            </div>

            <div className="form-group checkbox-group">
              <label>
                <input
                  type="checkbox"
                  checked={enableNlp}
                  onChange={(e) => setEnableNlp(e.target.checked)}
                />
                Enable NLP Analysis (key phrases, sentiment, etc.)
              </label>
            </div>

            {error && <div className="error">{error}</div>}

            <button type="submit" disabled={loading || !file} className="submit-button">
              {loading ? 'Uploading...' : 'Transcribe'}
            </button>
          </form>
        </div>

        <div className="jobs-section">
          <h2>Transcription Jobs</h2>
          {jobs.length === 0 ? (
            <p className="no-jobs">No transcription jobs yet</p>
          ) : (
            <div className="jobs-list">
              {jobs.map((job) => (
                <div key={job.job_id} className={`job-card ${job.status}`}>
                  <div className="job-header">
                    <h3>{job.filename}</h3>
                    <span className={`status-badge ${job.status}`}>
                      {job.status}
                    </span>
                  </div>
                  <div className="job-info">
                    <p><strong>Method:</strong> {job.method}</p>
                    <p><strong>ID:</strong> {job.job_id}</p>
                    {job.progress && <p><strong>Progress:</strong> {job.progress}</p>}
                    {job.error && <p className="error"><strong>Error:</strong> {job.error}</p>}
                  </div>
                  
                  {job.status === 'completed' && job.result && (
                    <div className="results">
                      <h4>Transcription Result:</h4>
                      <div className="transcription-text">
                        {job.result.transcription.full_text}
                      </div>
                      
                      {job.result.transcription.metadata && (
                        <div className="metadata">
                          <p><strong>Duration:</strong> {job.result.transcription.duration.toFixed(2)}s</p>
                          <p><strong>Language:</strong> {job.result.transcription.language}</p>
                          {job.result.transcription.metadata.speaker_count && (
                            <p><strong>Speakers:</strong> {job.result.transcription.metadata.speaker_count}</p>
                          )}
                        </div>
                      )}

                      {job.result.transcription.segments && (
                        <div className="segments">
                          <h4>Segments ({job.result.transcription.segments.length}):</h4>
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
                              <p className="more">... and {job.result.transcription.segments.length - 5} more segments</p>
                            )}
                          </div>
                        </div>
                      )}

                      {job.result.nlp_analysis && (
                        <div className="nlp-results">
                          <h4>NLP Analysis:</h4>
                          {job.result.nlp_analysis.key_phrases && (
                            <div className="key-phrases">
                              <strong>Key Phrases:</strong>
                              <div className="tags">
                                {job.result.nlp_analysis.key_phrases.slice(0, 10).map((phrase, idx) => (
                                  <span key={idx} className="tag">{phrase.text}</span>
                                ))}
                              </div>
                            </div>
                          )}
                          {job.result.nlp_analysis.sentiment && (
                            <div className="sentiment">
                              <strong>Sentiment:</strong> {job.result.nlp_analysis.sentiment.overall}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                  
                  <button onClick={() => deleteJob(job.job_id)} className="delete-button">
                    Delete
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
