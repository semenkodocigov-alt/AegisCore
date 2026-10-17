import React, { useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { LoginForm } from './LoginForm';
import { RegisterForm } from './RegisterForm';

interface WelcomeScreenProps {
  onContinueAsGuest: () => void;
}

export const WelcomeScreen: React.FC<WelcomeScreenProps> = ({ onContinueAsGuest }) => {
  const [mode, setMode] = useState<'login' | 'register'>('login');

  return (
    <main className="welcome-page">
      <section className="welcome-story" aria-label="About Aegis Core">
        <div className="brand-lockup">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none">
              <path d="M12 2.5 4 6v5.3c0 5 3.4 9.4 8 10.7 4.6-1.3 8-5.7 8-10.7V6l-8-3.5Z" />
              <path d="m8.8 12.3 2.1 2.1 4.5-4.7" />
            </svg>
          </span>
          <span className="brand-name">Aegis <span>Core</span></span>
        </div>

        <div className="welcome-copy">
          <p className="eyebrow">PERSONAL SECURITY, WITHOUT THE NOISE</p>
          <h1>A clearer view<br />of your device.</h1>
          <p className="welcome-description">
            Scan files, review what needs attention, and keep control close at hand.
            Your work stays on this device.
          </p>
        </div>

        <div className="welcome-notes">
          <div className="welcome-note">
            <span className="note-index">01</span>
            <div><strong>Local by default</strong><span>Files are inspected on your device.</span></div>
          </div>
          <div className="welcome-note">
            <span className="note-index">02</span>
            <div><strong>Start without an account</strong><span>Guest access is ready whenever you are.</span></div>
          </div>
        </div>

        <p className="welcome-footnote">Aegis Core <span>·</span> Desktop security workspace</p>
      </section>

      <section className="welcome-auth" aria-label={mode === 'login' ? 'Sign in' : 'Create account'}>
        <div className="auth-panel">
          <div className="auth-panel-heading">
            <p className="eyebrow">YOUR WORKSPACE</p>
            <h2>{mode === 'login' ? 'Welcome back.' : 'Make it yours.'}</h2>
            <p>{mode === 'login' ? 'Sign in to continue where you left off.' : 'Create an account for a persistent profile.'}</p>
          </div>

          <div className="auth-switch" role="tablist" aria-label="Account access">
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'login'}
              className={mode === 'login' ? 'auth-switch-active' : ''}
              onClick={() => setMode('login')}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'register'}
              className={mode === 'register' ? 'auth-switch-active' : ''}
              onClick={() => setMode('register')}
            >
              Create account
            </button>
          </div>

          <AnimatePresence mode="wait" initial={false}>
            <motion.div
              key={mode}
              initial={{ opacity: 0, y: 7 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -5 }}
              transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
            >
              {mode === 'login' ? (
                <LoginForm onSwitchToRegister={() => setMode('register')} />
              ) : (
                <RegisterForm onSwitchToLogin={() => setMode('login')} />
              )}
            </motion.div>
          </AnimatePresence>

          <div className="auth-divider"><span>OR</span></div>
          <motion.button
            type="button"
            className="button button-secondary guest-button"
            onClick={onContinueAsGuest}
            whileTap={{ scale: 0.985 }}
            transition={{ type: 'spring', stiffness: 420, damping: 28 }}
          >
            Continue as guest <span aria-hidden="true">→</span>
          </motion.button>
          <p className="auth-privacy-note">Guest access is session-only. No email or password required.</p>
        </div>
      </section>
    </main>
  );
};
