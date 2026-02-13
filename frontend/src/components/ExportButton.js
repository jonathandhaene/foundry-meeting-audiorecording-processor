import React, { useState } from 'react';
import axios from 'axios';
import { useTranslation } from 'react-i18next';
import './ExportButton.css';

function ExportButton({ jobId, transcription, nlpAnalysis, filename }) {
  const { t } = useTranslation();
  const [exporting, setExporting] = useState(false);
  const [showMenu, setShowMenu] = useState(false);

  const handleExport = async (format) => {
    setExporting(true);
    setShowMenu(false);

    try {
      const formData = new FormData();
      formData.append('format', format);
      
      const response = await axios.post(`/api/export/${jobId}`, 
        formData,
        { 
          responseType: 'blob',
          headers: {
            'Content-Type': 'multipart/form-data'
          }
        }
      );

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      
      const extension = format === 'txt' ? 'txt' : format === 'docx' ? 'docx' : 'pdf';
      const baseFilename = filename ? filename.replace(/\.[^/.]+$/, '') : 'transcript';
      link.setAttribute('download', `${baseFilename}.${extension}`);
      
      document.body.appendChild(link);
      link.click();
      link.parentNode.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Export failed:', error);
      alert(t('export.error', { defaultValue: 'Export failed. Please try again.' }));
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="export-button-container">
      <button 
        className="export-button"
        onClick={() => setShowMenu(!showMenu)}
        disabled={exporting}
        aria-haspopup="true"
        aria-expanded={showMenu}
      >
        {exporting ? t('export.exporting', { defaultValue: 'Exporting...' }) : t('export.button', { defaultValue: 'Export' })}
        <span className="export-icon">⬇</span>
      </button>
      
      {showMenu && (
        <div className="export-menu" role="menu">
          <button 
            className="export-menu-item"
            onClick={() => handleExport('txt')}
            role="menuitem"
          >
            {t('export.formats.txt', { defaultValue: 'Plain Text (.txt)' })}
          </button>
          <button 
            className="export-menu-item"
            onClick={() => handleExport('docx')}
            role="menuitem"
          >
            {t('export.formats.docx', { defaultValue: 'Word Document (.docx)' })}
          </button>
          <button 
            className="export-menu-item"
            onClick={() => handleExport('pdf')}
            role="menuitem"
          >
            {t('export.formats.pdf', { defaultValue: 'PDF Document (.pdf)' })}
          </button>
        </div>
      )}
    </div>
  );
}

export default ExportButton;
