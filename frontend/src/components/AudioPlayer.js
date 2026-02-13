import React, { useRef, useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import './AudioPlayer.css';

// Configuration
const MAX_TIMELINE_SEGMENTS = 20; // Maximum segments to display on timeline

function AudioPlayer({ jobId, segments, onTimeUpdate }) {
  const { t } = useTranslation();
  const audioRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      if (onTimeUpdate) {
        onTimeUpdate(audio.currentTime);
      }
    };

    const handleLoadedMetadata = () => {
      setDuration(audio.duration);
    };

    const handleEnded = () => {
      setIsPlaying(false);
    };

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [onTimeUpdate]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;

    if (isPlaying) {
      audio.pause();
    } else {
      audio.play();
    }
    setIsPlaying(!isPlaying);
  };

  const handleSeek = (e) => {
    const audio = audioRef.current;
    if (!audio) return;

    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const percentage = x / rect.width;
    audio.currentTime = percentage * duration;
  };

  const jumpToTime = (time) => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = time;
  };

  const handleVolumeChange = (e) => {
    const newVolume = parseFloat(e.target.value);
    setVolume(newVolume);
    if (audioRef.current) {
      audioRef.current.volume = newVolume;
    }
  };

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="audio-player">
      <audio 
        ref={audioRef} 
        src={`/api/audio/${jobId}`}
        preload="metadata"
      />
      
      <div className="player-controls">
        <button 
          className="play-button"
          onClick={togglePlay}
          aria-label={isPlaying ? t('audio.pause', { defaultValue: 'Pause' }) : t('audio.play', { defaultValue: 'Play' })}
        >
          {isPlaying ? '⏸' : '▶'}
        </button>

        <div className="time-display">
          {formatTime(currentTime)} / {formatTime(duration)}
        </div>

        <div 
          className="progress-track"
          onClick={handleSeek}
          role="slider"
          aria-label={t('audio.seek', { defaultValue: 'Seek' })}
          aria-valuemin="0"
          aria-valuemax={duration}
          aria-valuenow={currentTime}
        >
          <div 
            className="progress-filled"
            style={{ width: `${(currentTime / duration) * 100}%` }}
          />
        </div>

        <div className="volume-control">
          <span className="volume-icon">🔊</span>
          <input
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={volume}
            onChange={handleVolumeChange}
            className="volume-slider"
            aria-label={t('audio.volume', { defaultValue: 'Volume' })}
          />
        </div>
      </div>

      {segments && segments.length > 0 && (
        <div className="segment-timeline">
          {segments.slice(0, MAX_TIMELINE_SEGMENTS).map((segment, idx) => (
            <button
              key={idx}
              className="segment-marker"
              onClick={() => jumpToTime(segment.start_time)}
              style={{ left: `${(segment.start_time / duration) * 100}%` }}
              title={`Jump to ${formatTime(segment.start_time)}: ${segment.text.substring(0, 50)}...`}
              aria-label={`Jump to ${formatTime(segment.start_time)}`}
            >
              {segment.speaker_id && (
                <span className="marker-label">{segment.speaker_id}</span>
              )}
            </button>
          ))}
          {segments.length > MAX_TIMELINE_SEGMENTS && (
            <div className="timeline-note">
              Showing {MAX_TIMELINE_SEGMENTS} of {segments.length} segments
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default AudioPlayer;
