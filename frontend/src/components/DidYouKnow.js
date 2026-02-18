import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import './DidYouKnow.css';

const funFacts = [
  { key: 'fact1', default: '🌍 There are over 7,000 languages spoken in the world today!' },
  { key: 'fact2', default: '🎤 The first voice recording ever made was "Mary had a little lamb" in 1877!' },
  { key: 'fact3', default: '🤖 AI transcription can now recognize speech in over 100 languages!' },
  { key: 'fact4', default: '🗣️ Speaker diarization helps identify who said what in a conversation!' },
  { key: 'fact5', default: '🎵 The human voice range is typically 85-255 Hz for males and 165-255 Hz for females!' },
  { key: 'fact6', default: '📝 Transcription accuracy has improved by over 30% in the last 5 years!' },
  { key: 'fact7', default: '🌏 Mandarin Chinese is the most spoken native language with over 900 million speakers!' },
  { key: 'fact8', default: '🔊 Audio processing can remove background noise while preserving speech quality!' },
  { key: 'fact9', default: '💬 The average person speaks at 110-150 words per minute!' },
  { key: 'fact10', default: '🎙️ Professional transcriptionists can type 75-100 words per minute!' },
  { key: 'fact11', default: '🧠 NLP can extract sentiment and key phrases from transcribed text!' },
  { key: 'fact12', default: '🌟 Whisper AI can transcribe and translate simultaneously!' },
  { key: 'fact13', default: '📊 Voice recognition technology dates back to the 1950s!' },
  { key: 'fact14', default: '🎯 Custom vocabulary improves transcription accuracy by up to 15%!' },
  { key: 'fact15', default: '🌈 Some languages have sounds that do not exist in others!' }
];

function DidYouKnow() {
  const { t } = useTranslation();
  const [showFact, setShowFact] = useState(false);
  const [currentFact, setCurrentFact] = useState(null);
  const [confetti, setConfetti] = useState(false);

  useEffect(() => {
    // Check if it's a special date
    const today = new Date();
    const isSpecialDate = checkSpecialDate(today);
    
    // Show fact on mount
    const randomFact = funFacts[Math.floor(Math.random() * funFacts.length)];
    setCurrentFact(randomFact);
    
    // Delay to create entrance animation
    setTimeout(() => {
      setShowFact(true);
      
      if (isSpecialDate) {
        setConfetti(true);
        setTimeout(() => setConfetti(false), 5000);
      }
    }, 500);
  }, []);

  const checkSpecialDate = (date) => {
    const month = date.getMonth() + 1;
    const day = date.getDate();
    
    // Check for various holidays
    // New Year
    if (month === 1 && day === 1) return true;
    // Valentine's Day
    if (month === 2 && day === 14) return true;
    // Pi Day
    if (month === 3 && day === 14) return true;
    // Halloween
    if (month === 10 && day === 31) return true;
    // Christmas
    if (month === 12 && day === 25) return true;
    
    return false;
  };

  const handleClose = () => {
    setShowFact(false);
  };

  if (!showFact || !currentFact) return null;

  return (
    <>
      {confetti && (
        <div className="confetti-container">
          {[...Array(50)].map((_, i) => (
            <div
              key={i}
              className="confetti"
              style={{
                left: `${Math.random() * 100}%`,
                animationDelay: `${Math.random() * 3}s`,
                backgroundColor: ['#667eea', '#764ba2', '#f39c12', '#2ecc71', '#e74c3c'][Math.floor(Math.random() * 5)]
              }}
            />
          ))}
        </div>
      )}
      
      <div className={`did-you-know ${showFact ? 'show' : ''}`}>
        <div className="did-you-know-content">
          <span className="did-you-know-title">
            💡 {t('didYouKnow.title', { defaultValue: 'Did You Know?' })}
          </span>
          <span className="did-you-know-text">
            {t(`didYouKnow.${currentFact.key}`, { defaultValue: currentFact.default })}
          </span>
          <button
            className="close-button"
            onClick={handleClose}
            aria-label={t('didYouKnow.close', { defaultValue: 'Close' })}
          >
            ×
          </button>
        </div>
      </div>
    </>
  );
}

export default DidYouKnow;
