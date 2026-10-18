import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { apiService } from '../../services/api';
import { VirusTotalSettings as VirusTotalSettingsData } from '../../types/desktop';
import { useLanguage } from '../../context/LanguageContext';

const emptySettings: VirusTotalSettingsData = {
  configured: false,
  apiKeyHint: '',
  enabled: false,
  uploadUnknown: false,
};

export const VirusTotalSettings: React.FC = () => {
  const { t } = useLanguage();
  const [settings, setSettings] = useState(emptySettings);
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [isError, setIsError] = useState(false);

  useEffect(() => {
    let active = true;
    void apiService.getVirusTotalSettings().then((response) => {
      if (!active) return;
      if (response.success && response.data) {
        setSettings(response.data);
      } else {
        setFeedback(response.error?.message || 'VirusTotal settings could not be loaded.');
        setIsError(true);
      }
    }).catch(() => {
      if (active) {
        setFeedback('VirusTotal settings could not be loaded.');
        setIsError(true);
      }
    }).finally(() => {
      if (active) setIsLoading(false);
    });
    return () => { active = false; };
  }, []);

  const saveKey = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setIsSaving(true);
    setFeedback('');
    setIsError(false);
    try {
      const response = await apiService.testSaveVirusTotalKey(
        apiKey,
        settings.enabled,
        settings.uploadUnknown,
      );
      if (!response.success || !response.data) {
        setFeedback(response.error?.message || 'VirusTotal settings could not be saved.');
        setIsError(true);
        return;
      }
      setSettings(response.data);
      setApiKey('');
      setFeedback(response.data.message);
    } catch {
      setFeedback('Could not connect to VirusTotal.');
      setIsError(true);
    } finally {
      setIsSaving(false);
    }
  };

  const changeOptions = async (enabled: boolean, uploadUnknown: boolean) => {
    setIsSaving(true);
    setFeedback('');
    setIsError(false);
    try {
      const response = await apiService.setVirusTotalOptions(enabled, uploadUnknown);
      if (!response.success || !response.data) {
        setFeedback(response.error?.message || 'VirusTotal settings could not be saved.');
        setIsError(true);
        return;
      }
      setSettings(response.data);
      setFeedback(enabled ? 'VirusTotal scanning is enabled.' : 'VirusTotal scanning is disabled.');
    } catch {
      setFeedback('VirusTotal settings could not be saved.');
      setIsError(true);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <motion.section
      className="account-card virustotal-card"
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
    >
      <div className="card-heading">
        <div>
          <p className="eyebrow">{t('OPTIONAL CLOUD LOOKUP')}</p>
          <h2>{t('VirusTotal Integration')}</h2>
        </div>
        <span className={`virustotal-state ${settings.enabled ? 'virustotal-state-on' : ''}`}>
          {isLoading ? t('Loading…') : t(settings.enabled ? 'Enabled' : 'Disabled')}
        </span>
      </div>
      <p className="account-copy">
        {t('Check file hashes against VirusTotal. File contents are not uploaded unless you explicitly enable uploads below.')}
      </p>

      <form className="virustotal-key-form" onSubmit={(event) => void saveKey(event)}>
        <label className="field">
          <span className="field-label">{t('VirusTotal API key')}</span>
          <span className="virustotal-key-control">
            <input
              className="field-control"
              type={showKey ? 'text' : 'password'}
              autoComplete="new-password"
              maxLength={64}
              spellCheck={false}
              value={apiKey}
              onChange={(event) => setApiKey(event.target.value)}
              placeholder={settings.configured ? `${t('Saved key')}: ${settings.apiKeyHint}` : t('Paste your 64-character API key')}
              disabled={isLoading || isSaving}
              aria-label={t('VirusTotal API key')}
            />
            <button
              className="button button-secondary"
              type="button"
              onClick={() => setShowKey((visible) => !visible)}
              aria-label={t(showKey ? 'Hide API key' : 'Show API key')}
              aria-pressed={showKey}
            >
              {t(showKey ? 'Hide' : 'Show')}
            </button>
          </span>
        </label>
        <button className="button button-primary" type="submit" disabled={isLoading || isSaving}>
          {isSaving ? t('Testing key…') : t('Test / Save key')}
        </button>
      </form>

      <div className="virustotal-options">
        <label className="check-row settings-check-row">
          <input
            type="checkbox"
            checked={settings.enabled}
            disabled={isLoading || isSaving}
            onChange={(event) => void changeOptions(event.target.checked, settings.uploadUnknown)}
          />
          <span>{t('Enable VirusTotal scanning')}</span>
        </label>
        <label className="check-row settings-check-row">
          <input
            type="checkbox"
            checked={settings.uploadUnknown}
            disabled={isLoading || isSaving || !settings.configured}
            onChange={(event) => void changeOptions(settings.enabled, event.target.checked)}
          />
          <span>{t('Upload unknown files smaller than 32 MB')}</span>
        </label>
      </div>
      <p className="virustotal-privacy-note">{t('Uploads send file contents to VirusTotal and use your account quota.')}</p>

      {feedback && (
        <p className={`virustotal-feedback ${isError ? 'virustotal-feedback-error' : ''}`} role={isError ? 'alert' : 'status'}>
          {t(feedback)}
        </p>
      )}
    </motion.section>
  );
};
