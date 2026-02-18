import React, { useState, useRef, useEffect, useCallback } from 'react';
import './InfoTooltip.css';

function InfoTooltip({ text }) {
  const [visible, setVisible] = useState(false);
  const [position, setPosition] = useState('top');
  const triggerRef = useRef(null);
  const tooltipRef = useRef(null);

  const updatePosition = useCallback(() => {
    if (!triggerRef.current) return;
    const rect = triggerRef.current.getBoundingClientRect();
    // If too close to top, show below
    if (rect.top < 120) {
      setPosition('bottom');
    } else {
      setPosition('top');
    }
  }, []);

  useEffect(() => {
    if (visible) {
      updatePosition();
    }
  }, [visible, updatePosition]);

  return (
    <span className="info-tooltip-wrapper">
      <button
        type="button"
        ref={triggerRef}
        className="info-tooltip-trigger"
        aria-label="More information"
        aria-expanded={visible}
        onMouseEnter={() => setVisible(true)}
        onMouseLeave={() => setVisible(false)}
        onFocus={() => setVisible(true)}
        onBlur={() => setVisible(false)}
        onClick={(e) => {
          e.preventDefault();
          setVisible((v) => !v);
        }}
      >
        i
      </button>
      {visible && (
        <span
          ref={tooltipRef}
          className={`info-tooltip-content info-tooltip-${position}`}
          role="tooltip"
        >
          {text}
        </span>
      )}
    </span>
  );
}

export default InfoTooltip;
