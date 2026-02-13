import React from 'react';
import './ProgressBar.css';

function ProgressBar({ progress, status }) {
  // Extract percentage from progress string if it contains one
  // or calculate based on status
  const extractPercentage = (progressText) => {
    if (!progressText) return 0;
    
    // First, try to extract explicit percentage
    const match = progressText.match(/(\d+)%/);
    if (match) {
      return parseInt(match[1], 10);
    }
    
    // Fallback: Map common progress keywords to approximate percentages
    // This is language-independent as it checks for common English keywords
    const lowerText = progressText.toLowerCase();
    if (lowerText.includes('start') || lowerText.includes('initial')) return 5;
    if (lowerText.includes('preprocess')) return 20;
    if (lowerText.includes('transcrib')) return 50;
    if (lowerText.includes('analyz')) return 80;
    if (lowerText.includes('complet')) return 100;
    
    // If no match, return a default based on status
    if (status === 'processing') return 50;
    if (status === 'completed') return 100;
    
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
