import React from 'react';
import './SpeakerAvatar.css';

const avatarEmojis = ['👤', '👨', '👩', '🧑', '👨‍💼', '👩‍💼', '👨‍🎓', '👩‍🎓', '👨‍🔬', '👩‍🔬', '👨‍💻', '👩‍💻'];

const avatarColors = [
  '#667eea', '#764ba2', '#f39c12', '#2ecc71', '#e74c3c',
  '#3498db', '#9b59b6', '#1abc9c', '#e67e22', '#34495e',
  '#16a085', '#c0392b'
];

function SpeakerAvatar({ speakerId, size = 'medium' }) {
  if (!speakerId) return null;

  // Extract speaker number (e.g., "Speaker 1" -> 1, "SPEAKER_01" -> 1)
  const speakerNum = parseInt(speakerId.match(/\d+/)?.[0] || '0');
  
  // Select avatar and color based on speaker number
  const avatarIndex = speakerNum % avatarEmojis.length;
  const colorIndex = speakerNum % avatarColors.length;
  
  const emoji = avatarEmojis[avatarIndex];
  const color = avatarColors[colorIndex];

  return (
    <div 
      className={`speaker-avatar speaker-avatar-${size}`}
      style={{ backgroundColor: color }}
      title={speakerId}
      aria-label={`Avatar for ${speakerId}`}
    >
      <span className="speaker-avatar-emoji">{emoji}</span>
    </div>
  );
}

export default SpeakerAvatar;
