import React, { useState } from 'react';
import './TranscriptSearch.css';

function TranscriptSearch({ transcript, segments, onHighlight }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [matchCount, setMatchCount] = useState(0);
  const [currentMatch, setCurrentMatch] = useState(0);

  const handleSearch = (term) => {
    setSearchTerm(term);
    if (!term) {
      setMatchCount(0);
      setCurrentMatch(0);
      if (onHighlight) onHighlight(null);
      return;
    }

    // Count matches in the full transcript
    const regex = new RegExp(term, 'gi');
    const matches = transcript.match(regex);
    const count = matches ? matches.length : 0;
    setMatchCount(count);
    setCurrentMatch(count > 0 ? 1 : 0);

    if (count > 0 && onHighlight) {
      onHighlight({ term, index: 0 });
    }
  };

  const navigateMatch = (direction) => {
    if (matchCount === 0) return;
    
    let newIndex = currentMatch + direction;
    if (newIndex < 1) newIndex = matchCount;
    if (newIndex > matchCount) newIndex = 1;
    
    setCurrentMatch(newIndex);
    if (onHighlight) {
      onHighlight({ term: searchTerm, index: newIndex - 1 });
    }
  };

  const highlightText = (text) => {
    if (!searchTerm) return text;
    
    const parts = text.split(new RegExp(`(${searchTerm})`, 'gi'));
    return parts.map((part, index) => 
      part.toLowerCase() === searchTerm.toLowerCase() 
        ? <mark key={index} className="search-highlight">{part}</mark>
        : part
    );
  };

  return (
    <div className="transcript-search">
      <div className="search-controls">
        <input
          type="text"
          className="search-input"
          placeholder="Search transcript..."
          value={searchTerm}
          onChange={(e) => handleSearch(e.target.value)}
          aria-label="Search transcript"
        />
        {matchCount > 0 && (
          <div className="search-navigation">
            <span className="match-counter">{currentMatch} of {matchCount}</span>
            <button 
              onClick={() => navigateMatch(-1)} 
              className="nav-button"
              aria-label="Previous match"
              title="Previous match"
            >
              ↑
            </button>
            <button 
              onClick={() => navigateMatch(1)} 
              className="nav-button"
              aria-label="Next match"
              title="Next match"
            >
              ↓
            </button>
          </div>
        )}
      </div>
      {searchTerm && matchCount === 0 && (
        <div className="no-results">No matches found</div>
      )}
      {searchTerm && segments && (
        <div className="search-results">
          {segments.filter(seg => 
            seg.text.toLowerCase().includes(searchTerm.toLowerCase())
          ).slice(0, 10).map((segment, idx) => (
            <div key={idx} className="search-result-item">
              <span className="result-timestamp">[{segment.start_time.toFixed(1)}s]</span>
              {segment.speaker_id && (
                <span className="result-speaker">{segment.speaker_id}:</span>
              )}
              <span className="result-text">{highlightText(segment.text)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default TranscriptSearch;
