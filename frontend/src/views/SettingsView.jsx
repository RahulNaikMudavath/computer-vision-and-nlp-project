import React from 'react';

function SettingsView({
  settingsTheme,
  setSettingsTheme,
  settingsLanguage,
  setSettingsLanguage,
  settingsOcrLang,
  setSettingsOcrLang,
  settingsNotify,
  setSettingsNotify,
  handleSettingsUpdate
}) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem', maxWidth: '600px' }}>
      <div className="dashboard-title-area" style={{ marginBottom: 0 }}>
        <h1>System Preferences</h1>
        <p>Configure layout themes, notification channels, and default VLM options.</p>
      </div>

      <div className="controls-card glass-panel settings-form-layout">
        {/* Theme Settings */}
        <div className="form-group">
          <label className="form-label">Theme Selection</label>
          <div style={{ display: 'flex', gap: '1rem', marginTop: '0.25rem' }}>
            <button 
              onClick={() => { setSettingsTheme('light'); handleSettingsUpdate('light'); }}
              className={`btn-primary ${settingsTheme === 'light' ? '' : 'tab-btn'}`}
              style={{ flex: 1, background: settingsTheme === 'light' ? 'var(--primary)' : 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)' }}
            >
              Light Cyber
            </button>
            <button 
              onClick={() => { setSettingsTheme('dark'); handleSettingsUpdate('dark'); }}
              className={`btn-primary ${settingsTheme === 'dark' ? '' : 'tab-btn'}`}
              style={{ flex: 1, background: settingsTheme === 'dark' ? 'var(--primary)' : 'rgba(255,255,255,0.02)', border: '1px solid var(--border-color)' }}
            >
              Dark Cyberpunk
            </button>
          </div>
        </div>

        {/* Language Settings */}
        <div className="form-group">
          <label className="form-label">Display Language</label>
          <select 
            value={settingsLanguage} 
            onChange={(e) => { setSettingsLanguage(e.target.value); handleSettingsUpdate(null, e.target.value); }}
            className="filter-select"
            style={{ width: '100%', background: 'rgba(0,0,0,0.35)' }}
          >
            <option value="en">English (US)</option>
            <option value="es">Español</option>
            <option value="fr">Français</option>
          </select>
        </div>

        {/* Default OCR Language */}
        <div className="form-group">
          <label className="form-label">Default OCR Extraction Language</label>
          <select 
            value={settingsOcrLang} 
            onChange={(e) => { setSettingsOcrLang(e.target.value); handleSettingsUpdate(null, null, e.target.value); }}
            className="filter-select"
            style={{ width: '100%', background: 'rgba(0,0,0,0.35)' }}
          >
            <option value="en">English (Latin OCR)</option>
            <option value="hi">Hindi (Devanagari OCR)</option>
            <option value="multi">Multilingual VLM</option>
          </select>
        </div>

        {/* Email Notifications */}
        <div className="toggle-container" onClick={() => { const val = !settingsNotify; setSettingsNotify(val); handleSettingsUpdate(null, null, null, val); }}>
          <div className="toggle-label-container">
            <span className="toggle-title">Email Notifications</span>
            <span className="toggle-desc">Receive structured extraction alerts in your inbox.</span>
          </div>
          <label className="switch">
            <input 
              type="checkbox" 
              checked={settingsNotify} 
              onChange={() => {}} // handled by parent container click
            />
            <span className="slider"></span>
          </label>
        </div>
      </div>
    </div>
  );
}

export default SettingsView;
