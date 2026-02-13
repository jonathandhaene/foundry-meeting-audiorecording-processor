import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import './BadgeSystem.css';

const badges = [
  {
    id: 'first_transcription',
    name: 'First Steps',
    description: 'Complete your first transcription',
    icon: '🎉',
    condition: (stats) => stats.totalJobs >= 1
  },
  {
    id: 'five_transcriptions',
    name: 'Getting Started',
    description: 'Complete 5 transcriptions',
    icon: '⭐',
    condition: (stats) => stats.totalJobs >= 5
  },
  {
    id: 'ten_transcriptions',
    name: 'Professional',
    description: 'Complete 10 transcriptions',
    icon: '🏆',
    condition: (stats) => stats.totalJobs >= 10
  },
  {
    id: 'one_hour',
    name: 'Hour Master',
    description: 'Transcribe 1 hour of audio',
    icon: '⏱️',
    condition: (stats) => stats.totalDuration >= 3600
  },
  {
    id: 'five_hours',
    name: 'Time Keeper',
    description: 'Transcribe 5 hours of audio',
    icon: '🕐',
    condition: (stats) => stats.totalDuration >= 18000
  },
  {
    id: 'multilingual',
    name: 'Polyglot',
    description: 'Transcribe in 3 different languages',
    icon: '🌍',
    condition: (stats) => stats.languagesUsed >= 3
  },
  {
    id: 'nlp_user',
    name: 'NLP Explorer',
    description: 'Use NLP analysis 5 times',
    icon: '🧠',
    condition: (stats) => stats.nlpAnalysisCount >= 5
  },
  {
    id: 'diarization_expert',
    name: 'Speaker Pro',
    description: 'Use speaker diarization 10 times',
    icon: '🎤',
    condition: (stats) => stats.diarizationCount >= 10
  }
];

function BadgeSystem({ jobs, onNewBadge }) {
  const { t } = useTranslation();
  const [earnedBadges, setEarnedBadges] = useState([]);
  const [showPanel, setShowPanel] = useState(false);
  const [newBadge, setNewBadge] = useState(null);
  const [showConfetti, setShowConfetti] = useState(false);

  useEffect(() => {
    // Load earned badges from localStorage
    const saved = localStorage.getItem('earnedBadges');
    if (saved) {
      setEarnedBadges(JSON.parse(saved));
    }
  }, []);

  useEffect(() => {
    // Calculate stats from jobs
    const stats = calculateStats(jobs);
    
    // Check for new badges
    const newBadges = [];
    badges.forEach(badge => {
      if (badge.condition(stats) && !earnedBadges.includes(badge.id)) {
        newBadges.push(badge);
      }
    });
    
    if (newBadges.length > 0) {
      const updatedBadges = [...earnedBadges, ...newBadges.map(b => b.id)];
      setEarnedBadges(updatedBadges);
      localStorage.setItem('earnedBadges', JSON.stringify(updatedBadges));
      
      // Show first new badge notification (could be enhanced to show all sequentially)
      const firstBadge = newBadges[0];
      setNewBadge(firstBadge);
      setShowConfetti(true);
      
      setTimeout(() => {
        setNewBadge(null);
        setShowConfetti(false);
      }, 5000);
      
      if (onNewBadge) {
        newBadges.forEach(badge => onNewBadge(badge));
      }
    }
  }, [jobs, earnedBadges, onNewBadge]);

  const calculateStats = (jobs) => {
    const completedJobs = jobs.filter(j => j.status === 'completed');
    
    return {
      totalJobs: completedJobs.length,
      totalDuration: completedJobs.reduce((sum, j) => 
        sum + (j.result?.transcription?.duration || 0), 0
      ),
      languagesUsed: new Set(
        completedJobs
          .map(j => j.result?.transcription?.language)
          .filter(Boolean)
      ).size,
      nlpAnalysisCount: completedJobs.filter(j => j.result?.nlp_analysis).length,
      diarizationCount: completedJobs.filter(j => 
        j.result?.transcription?.metadata?.speaker_count > 0
      ).length
    };
  };

  const progress = (earnedBadges.length / badges.length) * 100;

  return (
    <>
      {showConfetti && (
        <div className="confetti-container">
          {[...Array(60)].map((_, i) => (
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
      
      {newBadge && (
        <div className="badge-notification">
          <div className="badge-notification-content">
            <div className="badge-icon-large">{newBadge.icon}</div>
            <h3>{t('badges.earned', { defaultValue: 'Badge Earned!' })}</h3>
            <h4>{t(`badges.${newBadge.id}.name`, { defaultValue: newBadge.name })}</h4>
            <p>{t(`badges.${newBadge.id}.description`, { defaultValue: newBadge.description })}</p>
          </div>
        </div>
      )}
      
      <button 
        className="badge-toggle"
        onClick={() => setShowPanel(!showPanel)}
        aria-label={t('badges.viewBadges', { defaultValue: 'View badges' })}
      >
        🏆
        {earnedBadges.length > 0 && (
          <span className="badge-count">{earnedBadges.length}</span>
        )}
      </button>
      
      {showPanel && (
        <>
          <div 
            className="badge-overlay"
            onClick={() => setShowPanel(false)}
            aria-hidden="true"
          />
          <div className="badge-panel">
            <h3>{t('badges.title', { defaultValue: 'Achievements' })}</h3>
            <div className="badge-progress">
              <div className="badge-progress-bar" style={{ width: `${progress}%` }} />
              <span className="badge-progress-text">
                {earnedBadges.length} / {badges.length}
              </span>
            </div>
            <div className="badge-grid">
              {badges.map(badge => {
                const earned = earnedBadges.includes(badge.id);
                return (
                  <div 
                    key={badge.id}
                    className={`badge-item ${earned ? 'earned' : 'locked'}`}
                    title={earned ? badge.name : '???'}
                  >
                    <div className="badge-icon">{earned ? badge.icon : '🔒'}</div>
                    <div className="badge-info">
                      <div className="badge-name">
                        {earned ? t(`badges.${badge.id}.name`, { defaultValue: badge.name }) : '???'}
                      </div>
                      <div className="badge-description">
                        {earned ? t(`badges.${badge.id}.description`, { defaultValue: badge.description }) : '???'}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </>
      )}
    </>
  );
}

export default BadgeSystem;
