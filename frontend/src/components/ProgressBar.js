import React from 'react';
import './ProgressBar.css';

function ProgressBar({ progress, status }) {
  // Extract percentage from progress string if it contains one
  const extractPercentage = (progressText) => {
    if (!progressText) return 0;
    const match = progressText.match(/(\d+)%/);
    if (match) {
      return parseInt(match[1], 10);
    }
    // Map status to approximate percentages
    if (progressText.includes('Starting')) return 5;
    if (progressText.includes('Preprocessing')) return 20;
    if (progressText.includes('Transcribing')) return 50;
    if (progressText.includes('Analyzing')) return 80;
    if (progressText.includes('Completed')) return 100;
    return 0;
  };

  const percentage = extractPercentage(progress);
  const isComplete = status === 'completed';
  const isFailed = status === 'failed';

  return (
    <div className="progress-bar-container">
      <div className="progress-bar-text">
        <span>{progress || 'Initializing...'}</span>
        {percentage > 0 && <span className="percentage">{percentage}%</span>}
      </div>
      <div className="progress-bar">
        <div 
          className={`progress-bar-fill ${isFailed ? 'failed' : ''} ${isComplete ? 'completed' : ''}`}
          style={{ width: `${percentage}%` }}
        >
          {!isFailed && !isComplete && <div className="progress-bar-shimmer"></div>}
        </div>
      </div>
    </div>
  );
}

export default ProgressBar;
