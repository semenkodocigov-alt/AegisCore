import React from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../../context/AuthContext';

export const SettingsView: React.FC = () => {
  const { rememberMePreference, setRememberMePreference } = useAuth();

  return (
    <motion.section
      className="account-page settings-page"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 340, damping: 32 }}
    >
      <header className="page-heading">
        <div>
          <p className="eyebrow">APPLICATION</p>
          <h1>Settings</h1>
          <p>Adjust sign-in defaults and review how local scans work.</p>
        </div>
      </header>

      <div className="account-grid">
        <section className="account-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">SIGN-IN</p>
              <h2>Remember this device</h2>
            </div>
          </div>
          <p className="account-copy">
            Choose whether the next sign-in should keep your account after Aegis Core closes.
            This does not change the session that is already active.
          </p>
          <label className="check-row settings-check-row">
            <input
              type="checkbox"
              checked={rememberMePreference}
              onChange={(event) => setRememberMePreference(event.target.checked)}
            />
            <span>Use Remember Me by default</span>
          </label>
        </section>

        <section className="account-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">SCANNING</p>
              <h2>Local, on-demand checks</h2>
            </div>
          </div>
          <dl className="session-details">
            <div><dt>When scans run</dt><dd>When you start one</dd></div>
            <div><dt>Where files are checked</dt><dd>This device</dd></div>
            <div><dt>Background monitoring</dt><dd>Not enabled</dd></div>
          </dl>
          <p className="account-copy">
            File contents stay on this device. If VirusTotal credentials are
            configured, file hashes may be sent for an external lookup.
          </p>
        </section>
      </div>
    </motion.section>
  );
};
