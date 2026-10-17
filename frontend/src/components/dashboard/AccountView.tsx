import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { InputField } from '../auth/InputField';

export const AccountView: React.FC = () => {
  const {
    user,
    isGuest,
    isLoading,
    error,
    clearError,
    logout,
    updateProfile,
    upgradeGuestAccount,
    rememberMePreference,
  } = useAuth();
  const { theme, setTheme, availableThemes } = useTheme();
  const [nickname, setNickname] = useState(user?.nickname || '');
  const [email, setEmail] = useState(user?.email || '');
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [rememberUpgrade, setRememberUpgrade] = useState(rememberMePreference);
  const [showUpgrade, setShowUpgrade] = useState(false);
  const [message, setMessage] = useState('');
  const [profileError, setProfileError] = useState('');

  useEffect(() => {
    setNickname(user?.nickname || '');
    setEmail(user?.email || '');
  }, [user]);

  if (!user) return null;

  const saveProfile = async () => {
    clearError();
    setMessage('');
    setProfileError('');
    if (newPassword && !currentPassword) {
      setProfileError('Enter your current password to change it.');
      return;
    }
    const result = await updateProfile({
      nickname: nickname.trim(),
      email: isGuest ? undefined : email.trim(),
      currentPassword: currentPassword || undefined,
      newPassword: newPassword || undefined,
    });
    if (result.success) {
      setCurrentPassword('');
      setNewPassword('');
      setMessage('Profile saved.');
    } else {
      setProfileError(result.error || error || 'Profile could not be saved.');
    }
  };

  const upgrade = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    clearError();
    setProfileError('');
    setMessage('');
    const result = await upgradeGuestAccount({
      nickname: nickname.trim(),
      email: email.trim(),
      password: newPassword,
      rememberMe: rememberUpgrade,
    });
    if (result.success) {
      setShowUpgrade(false);
      setNewPassword('');
      setMessage('Your account is ready.');
    } else {
      setProfileError(result.error || 'Account could not be created.');
    }
  };

  const createdLabel = user.createdAt
    ? new Date(user.createdAt).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' })
    : '—';

  return (
    <motion.section
      className="account-page"
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ type: 'spring', stiffness: 340, damping: 32 }}
    >
      <header className="page-heading">
        <div>
          <p className="eyebrow">PREFERENCES & IDENTITY</p>
          <h1>My account</h1>
          <p>Manage your profile, session, and the way Aegis looks.</p>
        </div>
        <span className={`session-badge ${isGuest ? 'session-badge-guest' : ''}`}>
          <span />{isGuest ? 'Guest session' : 'Signed in'}
        </span>
      </header>

      {(message || profileError || error) && (
        <div className={`account-notice ${profileError || error ? 'account-notice-error' : ''}`} role="status">
          {profileError || error || message}
        </div>
      )}

      <div className="account-grid">
        <section className="account-card profile-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">PROFILE</p>
              <h2>Personal details</h2>
            </div>
            <div className="profile-avatar" aria-hidden="true">{user.nickname.slice(0, 1).toUpperCase()}</div>
          </div>
          <div className="profile-fields">
            <InputField
              label="Nickname"
              autoComplete="nickname"
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              maxLength={32}
              minLength={2}
              disabled={isLoading}
            />
            <InputField
              label="Email address"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={isGuest || isLoading}
              hint={isGuest ? 'Add an email when you create an account.' : undefined}
            />
            {!isGuest && (
              <div className="password-change">
                <p className="eyebrow">PASSWORD</p>
                <InputField
                  label="Current password"
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  disabled={isLoading}
                />
                <InputField
                  label="New password"
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  minLength={8}
                  disabled={isLoading}
                  hint="Leave blank to keep your current password."
                />
              </div>
            )}
          </div>
          {!isGuest && (
            <div className="card-actions">
              <span className="account-meta">Member since {createdLabel}</span>
              <motion.button
                className="button button-primary"
                type="button"
                onClick={saveProfile}
                disabled={isLoading}
                whileTap={{ scale: 0.985 }}
                transition={{ type: 'spring', stiffness: 420, damping: 28 }}
              >
                {isLoading ? 'Saving…' : 'Save changes'}
              </motion.button>
            </div>
          )}
          {isGuest && (
            <div className="card-actions">
              <span className="account-meta">Guest profiles stay on this device.</span>
              <motion.button
                className="button button-primary"
                type="button"
                onClick={saveProfile}
                disabled={isLoading}
                whileTap={{ scale: 0.985 }}
                transition={{ type: 'spring', stiffness: 420, damping: 28 }}
              >
                Save nickname
              </motion.button>
            </div>
          )}
        </section>

        <section className="account-card session-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">SESSION</p>
              <h2>{isGuest ? 'Browsing as a guest' : 'This device'}</h2>
            </div>
          </div>
          <p className="account-copy">
            {isGuest
              ? 'Your profile is temporary. Create an account to keep your identity between sessions.'
              : 'Your profile is stored locally. You can sign out from this device at any time.'}
          </p>
          <dl className="session-details">
            <div><dt>Account type</dt><dd>{isGuest ? 'Guest' : user.role}</dd></div>
            <div><dt>Next sign-in</dt><dd>{rememberMePreference ? 'Remember me' : 'Session only'}</dd></div>
            <div><dt>Email</dt><dd>{isGuest ? 'Not connected' : user.email}</dd></div>
          </dl>

          {isGuest && (
            <>
              {!showUpgrade ? (
                <button className="button button-secondary full-button" type="button" onClick={() => setShowUpgrade(true)}>
                  Create an account <span aria-hidden="true">→</span>
                </button>
              ) : (
                <form className="upgrade-form" onSubmit={upgrade}>
                  <p className="eyebrow">KEEP YOUR PROFILE</p>
                  <InputField
                    label="Email address"
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                  />
                  <InputField
                    label="Password"
                    type="password"
                    autoComplete="new-password"
                    value={newPassword}
                    onChange={(event) => setNewPassword(event.target.value)}
                    minLength={8}
                    required
                  />
                  <label className="check-row">
                    <input
                      type="checkbox"
                      checked={rememberUpgrade}
                      onChange={(event) => setRememberUpgrade(event.target.checked)}
                    />
                    <span>Remember me on this device</span>
                  </label>
                  <div className="upgrade-actions">
                    <button className="button button-secondary" type="button" onClick={() => setShowUpgrade(false)}>
                      Cancel
                    </button>
                    <button className="button button-primary" type="submit" disabled={isLoading}>
                      {isLoading ? 'Creating…' : 'Create account'}
                    </button>
                  </div>
                </form>
              )}
            </>
          )}

          <button className="sign-out-button" type="button" onClick={() => void logout()} disabled={isLoading}>
            Sign out of this device
          </button>
        </section>

        <section className="account-card theme-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">APPEARANCE</p>
              <h2>Choose a theme</h2>
            </div>
          </div>
          <p className="account-copy">Aegis remembers your choice on this device.</p>
          <div className="theme-options">
            {availableThemes.map((option) => (
              <button
                type="button"
                key={option.id}
                className={`theme-option ${theme === option.id ? 'theme-option-selected' : ''}`}
                onClick={() => setTheme(option.id)}
                aria-pressed={theme === option.id}
              >
                <span className={`theme-preview theme-preview-${option.id}`}>
                  <span /><span /><span />
                </span>
                <span className="theme-option-copy">
                  <strong>{option.name}</strong>
                  <small>{option.description}</small>
                </span>
                {theme === option.id && <span className="theme-check" aria-label="Selected">✓</span>}
              </button>
            ))}
          </div>
        </section>
      </div>
    </motion.section>
  );
};
