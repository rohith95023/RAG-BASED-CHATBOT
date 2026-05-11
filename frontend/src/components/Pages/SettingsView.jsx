import React, { useEffect, useMemo, useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import './Pages.css';

const SETTINGS_KEY = 'flashman_ui_settings';

const defaultSettings = {
  autoStopSpeechOnNavigate: true,
  showTimestamps: true,
  compactMessageDensity: false,
  defaultAnswerMode: 'gemini',
  responseStyle: 'balanced',
};

const loadStoredSettings = () => {
  try {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) return defaultSettings;
    return { ...defaultSettings, ...JSON.parse(raw) };
  } catch {
    return defaultSettings;
  }
};

const SettingsView = () => {
  const { user } = useAuth();
  const [settings, setSettings] = useState(loadStoredSettings);
  const [savedAt, setSavedAt] = useState(null);

  useEffect(() => {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
  }, [settings]);

  const profileItems = useMemo(
    () => [
      { label: 'Username', value: user?.username || 'local_dev' },
      { label: 'Email', value: user?.email || 'Not set' },
      { label: 'Role', value: user?.role || 'Local developer' },
    ],
    [user]
  );

  const updateSetting = (key, value) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSavedAt(new Date());
  };

  const resetSettings = () => {
    setSettings(defaultSettings);
    setSavedAt(new Date());
  };

  return (
    <div className="page-view">
      <div className="page-hero">
        <div className="page-heading">
          <div className="page-title">
            <div className="page-icon">S</div>
            <div>
              <h1>Settings</h1>
              <p>Adjust how FLASH MAN behaves locally, from speech handling to response style.</p>
            </div>
          </div>
        </div>

        <div className="page-actions">
          <button className="page-button" onClick={resetSettings} type="button">
            Reset Defaults
          </button>
        </div>
      </div>

      <div className="content-grid">
        <section className="section-card">
          <h2>Profile</h2>
          <div className="help-list">
            {profileItems.map((item) => (
              <div className="faq-item" key={item.label}>
                <div className="session-main">
                  <div className="session-title">{item.label}</div>
                  <div className="session-meta">{item.value}</div>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="section-card">
          <h2>Saved</h2>
          <p>These preferences are saved in your browser and apply immediately to the local UI.</p>
          <div className="empty-state-card">
            <div className="stat-label">Last saved</div>
            <div className="stat-value" style={{ fontSize: '1rem' }}>
              {savedAt ? savedAt.toLocaleString() : 'Not saved yet'}
            </div>
          </div>
        </section>
      </div>

      <div className="settings-grid settings-grid-tight" style={{ marginTop: 'var(--space-4)' }}>
        <section className="section-card">
          <h2>Conversation</h2>
          <div className="settings-card-grid settings-card-grid-two">
            <div className="setting-card-row">
              <div className="setting-main">
                <div className="setting-label">Default answer mode</div>
                <div className="setting-help">Choose which mode opens first in chat.</div>
              </div>
              <div className="setting-control">
                <select
                  className="setting-select"
                  value={settings.defaultAnswerMode}
                  onChange={(e) => updateSetting('defaultAnswerMode', e.target.value)}
                >
                  <option value="gemini">FLASH MAN</option>
                  <option value="document">Documents</option>
                </select>
              </div>
            </div>

            <div className="setting-card-row">
              <div className="setting-main">
                <div className="setting-label">Speech cancel on navigate</div>
                <div className="setting-help">Stops any spoken response when you leave the page.</div>
              </div>
              <input
                className="toggle"
                type="checkbox"
                checked={settings.autoStopSpeechOnNavigate}
                onChange={(e) => updateSetting('autoStopSpeechOnNavigate', e.target.checked)}
              />
            </div>

            <div className="setting-card-row">
              <div className="setting-main">
                <div className="setting-label">Show message timestamps</div>
                <div className="setting-help">Keep the compact time labels under assistant messages.</div>
              </div>
              <input
                className="toggle"
                type="checkbox"
                checked={settings.showTimestamps}
                onChange={(e) => updateSetting('showTimestamps', e.target.checked)}
              />
            </div>

            <div className="setting-card-row">
              <div className="setting-main">
                <div className="setting-label">Compact message density</div>
                <div className="setting-help">Tighten spacing in long conversation threads.</div>
              </div>
              <input
                className="toggle"
                type="checkbox"
                checked={settings.compactMessageDensity}
                onChange={(e) => updateSetting('compactMessageDensity', e.target.checked)}
              />
            </div>
          </div>
        </section>

        <section className="section-card">
          <h2>Response Style</h2>
          <div className="settings-card-grid settings-card-grid-one">
            <div className="setting-card-row">
              <div className="setting-main">
                <div className="setting-label">Tone</div>
                <div className="setting-help">How verbose and direct the assistant should feel.</div>
              </div>
              <div className="setting-control">
                <select
                  className="setting-select"
                  value={settings.responseStyle}
                  onChange={(e) => updateSetting('responseStyle', e.target.value)}
                >
                  <option value="concise">Concise</option>
                  <option value="balanced">Balanced</option>
                  <option value="detailed">Detailed</option>
                </select>
              </div>
            </div>

            <div className="empty-state-card settings-note-card">
              <h3>Note</h3>
              <p>
                The backend chat mode still uses <code>gemini</code> internally as a route value, but
                the UI labels and branding are now FLASH MAN.
              </p>
            </div>
          </div>
        </section>
      </div>
    </div>
  );
};

export default SettingsView;
