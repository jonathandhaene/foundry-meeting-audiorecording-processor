import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import './ThemeSelector.css';

function ThemeSelector() {
  const { t } = useTranslation();
  const [theme, setTheme] = useState('light');
  const [showSelector, setShowSelector] = useState(false);

  const themes = [
    { id: 'light', name: t('themes.light', { defaultValue: 'Light' }), icon: '☀️' },
    { id: 'dark', name: t('themes.dark', { defaultValue: 'Dark' }), icon: '🌙' },
    { id: 'ocean', name: t('themes.ocean', { defaultValue: 'Ocean' }), icon: '🌊' },
    { id: 'forest', name: t('themes.forest', { defaultValue: 'Forest' }), icon: '🌲' },
    { id: 'sunset', name: t('themes.sunset', { defaultValue: 'Sunset' }), icon: '🌅' }
  ];

  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  const changeTheme = (newTheme) => {
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
    setShowSelector(false);
  };

  const currentTheme = themes.find(t => t.id === theme);

  return (
    <div className="theme-selector-wrapper">
      <button 
        className="theme-toggle-btn"
        onClick={() => setShowSelector(!showSelector)}
        aria-label={t('themes.selectTheme', { defaultValue: 'Select theme' })}
        aria-expanded={showSelector}
      >
        {currentTheme?.icon || '🎨'}
      </button>
      
      {showSelector && (
        <div className="theme-selector-panel" role="menu">
          <h3>{t('themes.chooseTheme', { defaultValue: 'Choose a Theme' })}</h3>
          <div className="theme-options">
            {themes.map((themeOption) => (
              <button
                key={themeOption.id}
                className={`theme-option ${theme === themeOption.id ? 'active' : ''}`}
                onClick={() => changeTheme(themeOption.id)}
                role="menuitemradio"
                aria-checked={theme === themeOption.id}
              >
                <span className="theme-icon">{themeOption.icon}</span>
                <span className="theme-name">{themeOption.name}</span>
              </button>
            ))}
          </div>
        </div>
      )}
      
      {showSelector && (
        <div 
          className="theme-selector-overlay"
          onClick={() => setShowSelector(false)}
          aria-hidden="true"
        />
      )}
    </div>
  );
}

export default ThemeSelector;
