import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import './AccessibilityControls.css';

function AccessibilityControls() {
  const { t } = useTranslation();
  const [fontSize, setFontSize] = useState('normal');
  const [highContrast, setHighContrast] = useState(false);
  const [showControls, setShowControls] = useState(false);

  useEffect(() => {
    // Apply font size to body
    // Remove any existing font-size classes
    const fontSizeClasses = ['font-size-normal', 'font-size-large', 'font-size-xlarge'];
    fontSizeClasses.forEach(cls => document.body.classList.remove(cls));
    
    // Add the new font size class
    document.body.classList.add(`font-size-${fontSize}`);
    
    // Save preference
    localStorage.setItem('fontSize', fontSize);
  }, [fontSize]);

  useEffect(() => {
    // Apply high contrast
    if (highContrast) {
      document.body.classList.add('high-contrast');
    } else {
      document.body.classList.remove('high-contrast');
    }
    
    // Save preference
    localStorage.setItem('highContrast', highContrast);
  }, [highContrast]);

  useEffect(() => {
    // Load saved preferences
    const savedFontSize = localStorage.getItem('fontSize');
    const savedHighContrast = localStorage.getItem('highContrast');
    
    if (savedFontSize) setFontSize(savedFontSize);
    if (savedHighContrast === 'true') setHighContrast(true);
  }, []);

  return (
    <div className="accessibility-controls">
      <button
        className="accessibility-toggle"
        onClick={() => setShowControls(!showControls)}
        aria-label={t('accessibility.toggleControls', { defaultValue: 'Toggle accessibility controls' })}
        aria-expanded={showControls}
      >
        ♿
      </button>
      
      {showControls && (
        <div className="accessibility-panel" role="region" aria-label={t('accessibility.settings', { defaultValue: 'Accessibility Settings' })}>
          <h3>{t('accessibility.title', { defaultValue: 'Accessibility' })}</h3>
          
          <div className="control-group">
            <label htmlFor="fontSize">
              {t('accessibility.fontSize', { defaultValue: 'Font Size' })}
            </label>
            <select
              id="fontSize"
              value={fontSize}
              onChange={(e) => setFontSize(e.target.value)}
              className="control-select"
            >
              <option value="normal">{t('accessibility.fontNormal', { defaultValue: 'Normal' })}</option>
              <option value="large">{t('accessibility.fontLarge', { defaultValue: 'Large' })}</option>
              <option value="xlarge">{t('accessibility.fontXLarge', { defaultValue: 'Extra Large' })}</option>
            </select>
          </div>
          
          <div className="control-group">
            <label>
              <input
                type="checkbox"
                checked={highContrast}
                onChange={(e) => setHighContrast(e.target.checked)}
              />
              {t('accessibility.highContrast', { defaultValue: 'High Contrast Mode' })}
            </label>
          </div>
          
          <div className="control-info">
            <p>{t('accessibility.keyboardInfo', { defaultValue: 'Use Tab to navigate, Enter to activate buttons' })}</p>
          </div>
        </div>
      )}
    </div>
  );
}

export default AccessibilityControls;
