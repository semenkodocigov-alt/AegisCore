import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../../context/AuthContext';
import { useTheme } from '../../context/ThemeContext';
import { InputField } from '../auth/InputField';
import { useLanguage } from '../../context/LanguageContext';
import { LanguageSwitcher } from '../common/LanguageSwitcher';

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
  const { t, language } = useLanguage();
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
      setProfileError(t('Enter your current password to change it.'));
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
      setMessage(t('Profile saved.'));
    } else {
      setProfileError(result.error ? t(result.error) : error ? t(error) : t('Profile could not be saved.'));
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
      setMessage(t('Your account is ready.'));
    } else {
      setProfileError(result.error ? t(result.error) : t('Account could not be created.'));
    }
  };

  const createdLabel = user.createdAt
    ? new Date(user.createdAt).toLocaleDateString(language === 'ru' ? 'ru-RU' : 'en-US', { year: 'numeric', month: 'long', day: 'numeric' })
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
          <p className="eyebrow">{t('PREFERENCES & IDENTITY')}</p>
          <h1>{t('My account')}</h1>
          <p>{t('Manage your profile, session, and the way Aegis looks.')}</p>
        </div>
        <span className={`session-badge ${isGuest ? 'session-badge-guest' : ''}`}>
          <span />{t(isGuest ? 'Guest session' : 'Signed in')}
        </span>
      </header>

      {(message || profileError || error) && (
        <div className={`account-notice ${profileError || error ? 'account-notice-error' : ''}`} role="status">
          {profileError ? t(profileError) : error ? t(error) : message}
        </div>
      )}

      <div className="account-grid">
        <section className="account-card profile-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">{t('PROFILE')}</p>
              <h2>{t('Personal details')}</h2>
            </div>
            <div className="profile-avatar" aria-hidden="true">{user.nickname.slice(0, 1).toUpperCase()}</div>
          </div>
          <div className="profile-fields">
            <InputField
              label={t('Nickname')}
              autoComplete="nickname"
              value={nickname}
              onChange={(event) => setNickname(event.target.value)}
              maxLength={32}
              minLength={2}
              disabled={isLoading}
            />
            <InputField
              label={t('Email address')}
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={isGuest || isLoading}
              hint={isGuest ? t('Add an email when you create an account.') : undefined}
            />
            {!isGuest && (
              <div className="password-change">
                <p className="eyebrow">{t('PASSWORD')}</p>
                <InputField
                  label={t('Current password')}
                  type="password"
                  autoComplete="current-password"
                  value={currentPassword}
                  onChange={(event) => setCurrentPassword(event.target.value)}
                  disabled={isLoading}
                />
                <InputField
                  label={t('New password')}
                  type="password"
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(event) => setNewPassword(event.target.value)}
                  minLength={8}
                  disabled={isLoading}
                  hint={t('Leave blank to keep your current password.')}
                />
              </div>
            )}
          </div>
          {!isGuest && (
            <div className="card-actions">
              <span className="account-meta">{t('Member since {date}', { date: createdLabel })}</span>
              <motion.button
                className="button button-primary"
                type="button"
                onClick={saveProfile}
                disabled={isLoading}
                whileTap={{ scale: 0.985 }}
                transition={{ type: 'spring', stiffness: 420, damping: 28 }}
              >
                {isLoading ? t('Saving…') : t('Save changes')}
              </motion.button>
            </div>
          )}
          {isGuest && (
            <div className="card-actions">
              <span className="account-meta">{t('Guest profiles stay on this device.')}</span>
              <motion.button
                className="button button-primary"
                type="button"
                onClick={saveProfile}
                disabled={isLoading}
                whileTap={{ scale: 0.985 }}
                transition={{ type: 'spring', stiffness: 420, damping: 28 }}
              >
                {t('Save nickname')}
              </motion.button>
            </div>
          )}
        </section>

        <section className="account-card session-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">{t('SESSION')}</p>
              <h2>{t(isGuest ? 'Browsing as a guest' : 'This device')}</h2>
            </div>
          </div>
          <p className="account-copy">
            {isGuest
              ? t('Your profile is temporary. Create an account to keep your identity between sessions.')
              : t('Your profile is stored locally. You can sign out from this device at any time.')}
          </p>
          <dl className="session-details">
            <div><dt>{t('Account type')}</dt><dd>{isGuest ? t('Guest') : user.role}</dd></div>
            <div><dt>{t('Next sign-in')}</dt><dd>{rememberMePreference ? t('Remember me') : t('Session only')}</dd></div>
            <div><dt>{t('Email address')}</dt><dd>{isGuest ? t('Not connected') : user.email}</dd></div>
          </dl>

          {isGuest && (
            <>
              {!showUpgrade ? (
                <button className="button button-secondary full-button" type="button" onClick={() => setShowUpgrade(true)}>
                  {t('Create account')} <span aria-hidden="true">→</span>
                </button>
              ) : (
                <form className="upgrade-form" onSubmit={upgrade}>
                  <p className="eyebrow">{t('KEEP YOUR PROFILE')}</p>
                  <InputField
                    label={t('Email address')}
                    type="email"
                    autoComplete="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    required
                  />
                  <InputField
                    label={t('Password')}
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
                    <span>{t('Remember me on this device')}</span>
                  </label>
                  <div className="upgrade-actions">
                    <button className="button button-secondary" type="button" onClick={() => setShowUpgrade(false)}>
                      {t('Cancel')}
                    </button>
                    <button className="button button-primary" type="submit" disabled={isLoading}>
                      {isLoading ? t('Creating…') : t('Create account')}
                    </button>
                  </div>
                </form>
              )}
            </>
          )}

          <button className="sign-out-button" type="button" onClick={() => void logout()} disabled={isLoading}>
            {t('Sign out of this device')}
          </button>
        </section>

        <section className="account-card theme-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">{t('APPEARANCE')}</p>
              <h2>{t('Choose a theme')}</h2>
            </div>
          </div>
          <p className="account-copy">{t('Aegis remembers your choice on this device.')}</p>
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
                  <strong>{t(option.name)}</strong>
                  <small>{t(option.description)}</small>
                </span>
                {theme === option.id && <span className="theme-check" aria-label={t('Selected')}>✓</span>}
              </button>
            ))}
          </div>
        </section>
        <LanguageSwitcher />
      </div>
    </motion.section>
  );
};
