import React from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../../context/AuthContext';
import { useLanguage } from '../../context/LanguageContext';
import { LanguageSwitcher } from '../common/LanguageSwitcher';
import { VirusTotalSettings } from './VirusTotalSettings';

export const SettingsView: React.FC = () => {
  const { rememberMePreference, setRememberMePreference } = useAuth();
  const { t } = useLanguage();

  return (
    <motion.section
      className="account-page settings-page"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 340, damping: 32 }}
    >
      <header className="page-heading">
        <div>
          <p className="eyebrow">{t('APPLICATION')}</p>
          <h1>{t('Settings')}</h1>
          <p>{t('Adjust sign-in defaults and review how local scans work.')}</p>
        </div>
      </header>

      <div className="account-grid">
        <section className="account-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">{t('SIGN-IN')}</p>
              <h2>{t('Remember this device')}</h2>
            </div>
          </div>
          <p className="account-copy">
            {t('Choose whether the next sign-in should keep your account after Aegis Core closes. This does not change the session that is already active.')}
          </p>
          <label className="check-row settings-check-row">
            <input
              type="checkbox"
              checked={rememberMePreference}
              onChange={(event) => setRememberMePreference(event.target.checked)}
            />
            <span>{t('Use Remember Me by default')}</span>
          </label>
        </section>

        <section className="account-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">{t('SCANNING')}</p>
              <h2>{t('Local, on-demand checks')}</h2>
            </div>
          </div>
          <dl className="session-details">
            <div><dt>{t('When scans run')}</dt><dd>{t('When you start one')}</dd></div>
            <div><dt>{t('Where files are checked')}</dt><dd>{t('This device')}</dd></div>
            <div><dt>{t('Background monitoring')}</dt><dd>{t('Not enabled')}</dd></div>
          </dl>
          <p className="account-copy">
            {t('File contents stay on this device. If VirusTotal credentials are configured, file hashes may be sent for an external lookup.')}
          </p>
        </section>
      </div>
      <VirusTotalSettings />
      <LanguageSwitcher />
    </motion.section>
  );
};
