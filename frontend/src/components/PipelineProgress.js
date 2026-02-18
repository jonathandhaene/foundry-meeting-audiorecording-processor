import React, { useState, useEffect, useRef } from 'react';
import './PipelineProgress.css';

const STAGE_META = {
  preprocessing: { icon: '🎵', label: 'Audio Preprocessing' },
  transcription: { icon: '🎙', label: 'Transcription' },
  diarization:   { icon: '👥', label: 'Speaker Diarization' },
  nlp:           { icon: '🧠', label: 'NLP Analysis' },
};

const SUB_TASK_LABELS = {
  key_phrases: 'Key Phrases',
  sentiment: 'Sentiment',
  segment_sentiment: 'Per-Segment Sentiment',
  entities: 'Entity Recognition',
  action_items: 'Action Items',
  summary: 'Summary',
  fast_api: 'Fast Diarization API',
  realtime_fallback: 'Real-time Fallback',
  azure_speech: 'Azure Speech Analysis',
  merge: 'Speaker Merge',
};

const STAGE_ORDER = ['preprocessing', 'transcription', 'diarization', 'nlp'];

function PipelineProgress({ stages, progress, status, startedAt }) {
  const [elapsed, setElapsed] = useState(0);
  const [showDetails, setShowDetails] = useState(false);
  const intervalRef = useRef(null);

  // Elapsed time counter
  useEffect(() => {
    if (status === 'processing' || status === 'pending') {
      const start = startedAt ? new Date(startedAt).getTime() : Date.now();
      intervalRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - start) / 1000));
      }, 1000);
      return () => clearInterval(intervalRef.current);
    }
    return () => clearInterval(intervalRef.current);
  }, [status, startedAt]);

  const formatElapsed = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  // Filter to only stages present in the pipeline
  const activeStages = STAGE_ORDER.filter(k => stages && stages[k]);

  // Detect parallelism: stages that are both "running" at the same time
  const runningStages = activeStages.filter(k => stages[k]?.status === 'running');
  const isParallel = runningStages.length > 1;

  // Overall percentage
  const overallPct = activeStages.length > 0
    ? Math.round(
        activeStages.reduce((sum, k) => sum + (stages[k]?.progress || 0), 0)
        / activeStages.length
      )
    : 0;

  if (!stages || activeStages.length === 0) {
    // Fallback: simple text progress
    return (
      <div className="pipeline-progress">
        <div className="pipeline-fallback">
          <span className="pulse-dot" />
          <span>{progress || 'Processing...'}</span>
          {elapsed > 0 && (
            <span className="pipeline-elapsed">{formatElapsed(elapsed)}</span>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="pipeline-progress">
      {/* Header bar */}
      <div className="pipeline-header">
        <div className="pipeline-header-left">
          <span className="pulse-dot" />
          <span className="pipeline-title">
            {isParallel
              ? `⚡ Running ${runningStages.map(k => STAGE_META[k]?.label || k).join(' & ')} in parallel`
              : progress || 'Processing...'}
          </span>
        </div>
        <div className="pipeline-header-right">
          {elapsed > 0 && (
            <span className="pipeline-elapsed">{formatElapsed(elapsed)}</span>
          )}
          <span className="pipeline-overall-pct">{overallPct}%</span>
        </div>
      </div>

      {/* Overall progress bar */}
      <div className="pipeline-overall-bar">
        <div
          className="pipeline-overall-fill"
          style={{ width: `${overallPct}%` }}
        />
      </div>

      {/* Stage cards */}
      <div className={`pipeline-stages ${isParallel ? 'parallel-active' : ''}`}>
        {activeStages.map((key) => {
          const stage = stages[key];
          const meta = STAGE_META[key] || { icon: '⚙', label: key };
          const st = stage.status || 'pending';
          const pct = stage.progress || 0;

          return (
            <div key={key} className={`pipeline-stage stage-${st}`}>
              <div className="stage-icon-wrap">
                <span className="stage-icon">{meta.icon}</span>
                {st === 'running' && <span className="stage-spinner" />}
                {st === 'done' && <span className="stage-check">✓</span>}
                {st === 'error' && <span className="stage-error-icon">✗</span>}
              </div>
              <div className="stage-body">
                <div className="stage-label-row">
                  <span className="stage-label">{meta.label}</span>
                  {st === 'running' && <span className="stage-pct">{pct}%</span>}
                </div>
                <div className="stage-bar">
                  <div
                    className={`stage-bar-fill status-${st}`}
                    style={{ width: `${st === 'done' ? 100 : pct}%` }}
                  >
                    {st === 'running' && <div className="stage-bar-shimmer" />}
                  </div>
                </div>
                <span className="stage-detail">{stage.detail || ''}</span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Parallel indicator */}
      {isParallel && (
        <div className="parallel-badge">
          ⚡ {runningStages.length} tasks running in parallel — faster results
        </div>
      )}

      {/* Collapsible sub-task details */}
      {(() => {
        const stagesWithSubs = activeStages.filter(
          k => stages[k]?.sub_tasks && Object.keys(stages[k].sub_tasks).length > 0
        );
        if (stagesWithSubs.length === 0) return null;
        return (
          <div className="subtask-section">
            <button
              className="subtask-toggle"
              onClick={() => setShowDetails(d => !d)}
              type="button"
              aria-expanded={showDetails}
            >
              <span className={`subtask-chevron ${showDetails ? 'open' : ''}`}>▶</span>
              <span>Parallel Tasks Detail</span>
              <span className="subtask-count">
                {stagesWithSubs.reduce((n, k) => n + Object.keys(stages[k].sub_tasks).length, 0)} sub-tasks
              </span>
            </button>
            {showDetails && (
              <div className="subtask-details">
                {stagesWithSubs.map(key => {
                  const stage = stages[key];
                  const meta = STAGE_META[key] || { icon: '⚙', label: key };
                  return (
                    <div key={key} className="subtask-group">
                      <div className="subtask-group-header">
                        <span>{meta.icon} {meta.label}</span>
                      </div>
                      <div className="subtask-list">
                        {Object.entries(stage.sub_tasks).map(([name, st]) => (
                          <div key={name} className={`subtask-item subtask-${st}`}>
                            <span className="subtask-indicator">
                              {st === 'done' ? '✓' : st === 'running' ? '⟳' : st === 'error' ? '✗' : '○'}
                            </span>
                            <span className="subtask-name">{SUB_TASK_LABELS[name] || name}</span>
                            <span className={`subtask-status subtask-status-${st}`}>{st}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        );
      })()}
    </div>
  );
}

export default PipelineProgress;
