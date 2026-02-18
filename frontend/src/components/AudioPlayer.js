import React, { useRef, useState, useEffect, useCallback, forwardRef, useImperativeHandle } from 'react';
import { useTranslation } from 'react-i18next';
import './AudioPlayer.css';

// Speaker colors (same palette as SpeakerAvatar)
const SPEAKER_COLORS = [
  '#667eea', '#764ba2', '#f39c12', '#2ecc71', '#e74c3c',
  '#3498db', '#9b59b6', '#1abc9c', '#e67e22', '#34495e',
  '#16a085', '#c0392b',
];

const PLAYBACK_SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2];

function getSpeakerColor(speakerId) {
  if (!speakerId) return SPEAKER_COLORS[0];
  const num = parseInt(speakerId.match(/\d+/)?.[0] || '0', 10);
  return SPEAKER_COLORS[num % SPEAKER_COLORS.length];
}

function getSentimentColor(sentiment) {
  if (!sentiment) return '#95a5a6';
  switch (sentiment) {
    case 'positive': return '#27ae60';
    case 'negative': return '#e74c3c';
    case 'mixed': return '#f39c12';
    default: return '#95a5a6';
  }
}

const AudioPlayer = forwardRef(function AudioPlayer({ jobId, segments, onTimeUpdate, segmentSentiments }, ref) {
  const { t } = useTranslation();
  const audioRef = useRef(null);
  const playerRef = useRef(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1);
  const [isMuted, setIsMuted] = useState(false);

  // Expose seekTo to parent via ref
  useImperativeHandle(ref, () => ({
    seekTo(time) {
      const audio = audioRef.current;
      if (!audio) return;
      const doSeek = () => {
        audio.currentTime = time;
        if (!isPlaying) {
          const p = audio.play();
          if (p && p.then) {
            p.then(() => { audio.currentTime = time; });
          }
          setIsPlaying(true);
        }
      };
      if (audio.readyState >= 1) {
        doSeek();
      } else {
        audio.addEventListener('loadedmetadata', doSeek, { once: true });
        audio.load();
      }
    },
  }));

  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const handleTimeUpdate = () => {
      setCurrentTime(audio.currentTime);
      if (onTimeUpdate) onTimeUpdate(audio.currentTime);
    };
    const handleLoadedMetadata = () => setDuration(audio.duration);
    const handleEnded = () => setIsPlaying(false);

    audio.addEventListener('timeupdate', handleTimeUpdate);
    audio.addEventListener('loadedmetadata', handleLoadedMetadata);
    audio.addEventListener('ended', handleEnded);

    return () => {
      audio.removeEventListener('timeupdate', handleTimeUpdate);
      audio.removeEventListener('loadedmetadata', handleLoadedMetadata);
      audio.removeEventListener('ended', handleEnded);
    };
  }, [onTimeUpdate]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Only handle shortcuts when player is focused or no input is focused
      const tag = document.activeElement?.tagName?.toLowerCase();
      if (tag === 'input' || tag === 'textarea' || tag === 'select') return;

      const audio = audioRef.current;
      if (!audio) return;

      switch (e.key) {
        case ' ':
          e.preventDefault();
          togglePlay();
          break;
        case 'ArrowLeft':
          e.preventDefault();
          audio.currentTime = Math.max(0, audio.currentTime - 5);
          break;
        case 'ArrowRight':
          e.preventDefault();
          audio.currentTime = Math.min(effectiveDuration, audio.currentTime + 5);
          break;
        case 'ArrowUp':
          e.preventDefault();
          setVolume(v => {
            const newV = Math.min(1, v + 0.1);
            audio.volume = newV;
            return newV;
          });
          break;
        case 'ArrowDown':
          e.preventDefault();
          setVolume(v => {
            const newV = Math.max(0, v - 0.1);
            audio.volume = newV;
            return newV;
          });
          break;
        case 'm':
        case 'M':
          toggleMute();
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isPlaying, duration]);

  const togglePlay = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isPlaying) { audio.pause(); } else { audio.play(); }
    setIsPlaying(!isPlaying);
  };

  const toggleMute = () => {
    const audio = audioRef.current;
    if (!audio) return;
    if (isMuted) {
      audio.volume = volume;
      setIsMuted(false);
    } else {
      audio.volume = 0;
      setIsMuted(true);
    }
  };

  const skip = (seconds) => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = Math.max(0, Math.min(effectiveDuration, audio.currentTime + seconds));
  };

  const cyclePlaybackRate = () => {
    const audio = audioRef.current;
    if (!audio) return;
    const currentIdx = PLAYBACK_SPEEDS.indexOf(playbackRate);
    const nextIdx = (currentIdx + 1) % PLAYBACK_SPEEDS.length;
    const newRate = PLAYBACK_SPEEDS[nextIdx];
    audio.playbackRate = newRate;
    setPlaybackRate(newRate);
  };

  const handleSeek = (e) => {
    const audio = audioRef.current;
    if (!audio || !effectiveDuration) return;
    const rect = e.currentTarget.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    audio.currentTime = Math.max(0, Math.min(effectiveDuration, pct * effectiveDuration));
  };

  const handleVolumeChange = (e) => {
    const v = parseFloat(e.target.value);
    setVolume(v);
    setIsMuted(v === 0);
    if (audioRef.current) audioRef.current.volume = v;
  };

  const formatTime = (seconds) => {
    if (!seconds || isNaN(seconds)) return '0:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Build speaker spans for timeline
  const effectiveDuration = duration || (segments && segments.length > 0
    ? Math.max(...segments.map(s => s.end_time))
    : 0);

  const buildSpeakerSpans = useCallback(() => {
    if (!segments || segments.length === 0 || !effectiveDuration) return [];
    return segments.map((seg, idx) => {
      const left = (seg.start_time / effectiveDuration) * 100;
      const width = Math.max(0.3, ((seg.end_time - seg.start_time) / effectiveDuration) * 100);
      return {
        idx,
        left,
        width,
        color: getSpeakerColor(seg.speaker_id),
        speaker: seg.speaker_id || `Segment ${idx + 1}`,
        startTime: seg.start_time,
        text: seg.text,
      };
    });
  }, [segments, effectiveDuration]);

  // Build sentiment spans for timeline
  const buildSentimentSpans = useCallback(() => {
    if (!segmentSentiments || segmentSentiments.length === 0 || !effectiveDuration) return [];
    return segmentSentiments.map((ss, idx) => {
      const left = (ss.start / effectiveDuration) * 100;
      const segEnd = ss.end || (segmentSentiments[idx + 1]?.start || effectiveDuration);
      const width = Math.max(0.3, ((segEnd - ss.start) / effectiveDuration) * 100);
      return {
        idx,
        left,
        width,
        color: getSentimentColor(ss.sentiment),
        sentiment: ss.sentiment,
        speaker: ss.speaker,
        scores: ss.scores,
        startTime: ss.start,
      };
    });
  }, [segmentSentiments, effectiveDuration]);

  const speakerSpans = buildSpeakerSpans();
  const sentimentSpans = buildSentimentSpans();

  return (
    <div className="audio-player d365-player" ref={playerRef} tabIndex="-1">
      <audio ref={audioRef} src={`/api/audio/${jobId}`} preload="metadata" />

      {/* Main controls row */}
      <div className="player-controls">
        <button className="player-btn skip-btn" onClick={() => skip(-10)}
          title={t('audio.skipBack', { defaultValue: 'Skip back 10s' })}
          aria-label="Skip back 10 seconds">
          ⏪
        </button>

        <button className="player-btn play-button" onClick={togglePlay}
          aria-label={isPlaying ? t('audio.pause', { defaultValue: 'Pause' }) : t('audio.play', { defaultValue: 'Play' })}>
          {isPlaying ? '⏸' : '▶'}
        </button>

        <button className="player-btn skip-btn" onClick={() => skip(10)}
          title={t('audio.skipForward', { defaultValue: 'Skip forward 10s' })}
          aria-label="Skip forward 10 seconds">
          ⏩
        </button>

        <div className="time-display">
          {formatTime(currentTime)} / {formatTime(effectiveDuration)}
        </div>

        <button className="player-btn speed-btn" onClick={cyclePlaybackRate}
          title={`Playback speed: ${playbackRate}x`}
          aria-label={`Playback speed ${playbackRate}x, click to change`}>
          {playbackRate}x
        </button>

        <div className="volume-control">
          <button className="player-btn volume-btn" onClick={toggleMute}
            aria-label={isMuted ? 'Unmute' : 'Mute'}>
            {isMuted ? '🔇' : volume > 0.5 ? '🔊' : volume > 0 ? '🔉' : '🔈'}
          </button>
          <input type="range" min="0" max="1" step="0.05" value={isMuted ? 0 : volume}
            onChange={handleVolumeChange} className="volume-slider"
            aria-label={t('audio.volume', { defaultValue: 'Volume' })} />
        </div>
      </div>

      {/* Waveform / progress track */}
      <div className="progress-track-wrapper">
        <div className="progress-track" onClick={handleSeek}
          role="slider" aria-label={t('audio.seek', { defaultValue: 'Seek' })}
          aria-valuemin="0" aria-valuemax={effectiveDuration} aria-valuenow={currentTime}>
          <div className="progress-filled" style={{ width: `${effectiveDuration ? (currentTime / effectiveDuration) * 100 : 0}%` }} />
          {/* Playhead */}
          {effectiveDuration > 0 && (
            <div className="progress-playhead" style={{ left: `${(currentTime / effectiveDuration) * 100}%` }} />
          )}
        </div>
      </div>

      {/* Speaker timeline lane */}
      {speakerSpans.length > 0 && (
        <div className="timeline-lane">
          <div className="lane-label">Speakers</div>
          <div className="lane-track" onClick={handleSeek}>
            {speakerSpans.map((span) => (
              <button
                key={span.idx}
                className={`speaker-span ${span.startTime <= currentTime && currentTime < span.startTime + ((span.width / 100) * effectiveDuration) ? 'active' : ''}`}
                style={{
                  left: `${span.left}%`,
                  width: `${span.width}%`,
                  backgroundColor: span.color,
                }}
                onClick={() => {
                  const audio = audioRef.current;
                  if (!audio || !effectiveDuration) return;
                  audio.currentTime = span.startTime;
                  if (!isPlaying) { audio.play(); setIsPlaying(true); }
                }}
                title={`${span.speaker} – ${formatTime(span.startTime)}: ${span.text.substring(0, 60)}…`}
                aria-label={`${span.speaker} at ${formatTime(span.startTime)}`}
              />
            ))}
            {effectiveDuration > 0 && (
              <div className="timeline-playhead" style={{ left: `${(currentTime / effectiveDuration) * 100}%` }} />
            )}
          </div>
        </div>
      )}

      {/* Sentiment timeline lane (D365-style) */}
      {sentimentSpans.length > 0 && (
        <div className="timeline-lane sentiment-lane">
          <div className="lane-label">Sentiment</div>
          <div className="lane-track" onClick={handleSeek}>
            {sentimentSpans.map((span) => (
              <button
                key={span.idx}
                className="sentiment-span"
                style={{
                  left: `${span.left}%`,
                  width: `${span.width}%`,
                  backgroundColor: span.color,
                  border: 'none',
                  padding: 0,
                  cursor: 'pointer',
                }}
                onClick={() => {
                  const audio = audioRef.current;
                  if (!audio || !effectiveDuration) return;
                  audio.currentTime = span.startTime;
                  if (!isPlaying) { audio.play(); setIsPlaying(true); }
                }}
                title={`${span.sentiment} (${span.speaker}) – pos: ${(span.scores?.positive * 100).toFixed(0)}%, neg: ${(span.scores?.negative * 100).toFixed(0)}%`}
                aria-label={`${span.sentiment} sentiment at ${formatTime(span.startTime)}`}
              />
            ))}
            {effectiveDuration > 0 && (
              <div className="timeline-playhead" style={{ left: `${(currentTime / effectiveDuration) * 100}%` }} />
            )}
          </div>
        </div>
      )}

      {/* Keyboard shortcut hint */}
      <div className="player-shortcuts-hint">
        Space: play/pause · ←→: ±5s · ↑↓: volume · M: mute
      </div>
    </div>
  );
});

export default AudioPlayer;
