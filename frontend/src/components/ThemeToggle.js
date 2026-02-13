import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import './ThemeToggle.css';

function ThemeToggle() {
  const { t } = useTranslation();
  const [theme, setTheme] = useState('light');

  useEffect(() => {
    // Load theme from localStorage
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);
    document.documentElement.setAttribute('data-theme', savedTheme);
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'light' ? 'dark' : 'light';
    setTheme(newTheme);
    localStorage.setItem('theme', newTheme);
    document.documentElement.setAttribute('data-theme', newTheme);
  };

  return (
    <button 
      className="theme-toggle"
      onClick={toggleTheme}
      aria-label={t('theme.toggle', { defaultValue: `Switch to ${theme === 'light' ? 'dark' : 'light'} mode` })}
      title={t('theme.toggle', { defaultValue: `Switch to ${theme === 'light' ? 'dark' : 'light'} mode` })}
    >
      {theme === 'light' ? '🌙' : '☀️'}
    </button>
  );
}

export default ThemeToggle;
