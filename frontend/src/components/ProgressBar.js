import React, { useState, useEffect, useRef } from 'react';
import './ProgressBar.css';

const PROCESSING_TIPS = [
  'Audio is being analyzed in real time by Azure Speech Services...',
  'Longer recordings take more time — this is normal.',
  'Speaker diarization identifies who said what.',
  'Each recognized segment is being processed individually.',
  'The transcription will include timestamps for every segment.',
  'Sit tight — quality transcription takes a moment!',
];

function ProgressBar({ progress, status, startedAt }) {
  const [elapsed, setElapsed] = useState(0);
  const [tipIndex, setTipIndex] = useState(0);
  const intervalRef = useRef(null);

  // Elapsed time counter
  useEffect(() => {
    if (status === 'processing' || status === 'pending') {
      const start = startedAt ? new Date(startedAt).getTime() : Date.now();
      intervalRef.current = setInterval(() => {
        setElapsed(Math.floor((Date.now() - start) / 1000));
      }, 1000);
      return () => clearInterval(intervalRef.current);
    } else {
      clearInterval(intervalRef.current);
    }
  }, [status, startedAt]);

  // Rotate tips every 6 seconds
  useEffect(() => {
    if (status !== 'processing') return;
    const tipTimer = setInterval(() => {
      setTipIndex(prev => (prev + 1) % PROCESSING_TIPS.length);
    }, 6000);
    return () => clearInterval(tipTimer);
  }, [status]);

  const extractPercentage = (progressText) => {
    if (!progressText) return 0;
    const match = progressText.match(/(\d+)%/);
    if (match) return parseInt(match[1], 10);

    const lowerText = progressText.toLowerCase();
    if (lowerText.includes('start') || lowerText.includes('initial')) return 10;
    if (lowerText.includes('preprocess')) return 20;
    if (lowerText.includes('transcrib')) return 50;
    if (lowerText.includes('analyz')) return 85;
    if (lowerText.includes('complet')) return 100;

    if (status === 'processing') return 50;
    if (status === 'completed') return 100;
    return 0;
  };

  const formatElapsed = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return m > 0 ? `${m}m ${s}s` : `${s}s`;
  };

  const percentage = extractPercentage(progress);
  const isComplete = status === 'completed';
  const isFailed = status === 'failed';
  const isActive = status === 'processing' || status === 'pending';

  return (
    <div className="progress-bar-container">
      <div className="progress-bar-text">
        <span className="progress-status">
          {isActive && <span className="pulse-dot" />}
          {progress || 'Initializing...'}
        </span>
        <span className="progress-meta">
          {isActive && elapsed > 0 && (
            <span className="elapsed-time">{formatElapsed(elapsed)}</span>
          )}
          {percentage > 0 && <span className="percentage">{percentage}%</span>}
        </span>
      </div>
      <div className="progress-bar">
        <div
          className={`progress-bar-fill ${isFailed ? 'failed' : ''} ${isComplete ? 'completed' : ''}`}
          style={{ width: `${percentage}%` }}
        >
          {isActive && <div className="progress-bar-shimmer"></div>}
        </div>
      </div>
      {isActive && (
        <div className="progress-tip" key={tipIndex}>
          <span className="tip-icon">💡</span>
          <span className="tip-text">{PROCESSING_TIPS[tipIndex]}</span>
        </div>
      )}
    </div>
  );
}

export default ProgressBar;
