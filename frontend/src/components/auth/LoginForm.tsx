import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../../context/AuthContext';
import { InputField } from './InputField';
import { useLanguage } from '../../context/LanguageContext';

interface LoginFormProps {
  onSuccess?: () => void;
  onSwitchToRegister: () => void;
}

export const LoginForm: React.FC<LoginFormProps> = ({ onSuccess, onSwitchToRegister }) => {
  const { login, isLoading, error: authError, clearError, rememberMePreference } = useAuth();
  const { t } = useLanguage();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(rememberMePreference);
  const [validationError, setValidationError] = useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    clearError();
    setValidationError(null);

    const normalizedEmail = email.trim();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setValidationError(t('Enter a valid email address.'));
      return;
    }
    if (!password) {
      setValidationError(t('Enter your password.'));
      return;
    }

    const result = await login({ email: normalizedEmail, password, rememberMe });
    if (result.success) onSuccess?.();
  };

  return (
    <form className="auth-form" onSubmit={handleSubmit}>
      {(authError || validationError) && (
        <motion.div
          className="form-alert form-alert-error"
          role="alert"
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
        >
          {validationError || (authError ? t(authError) : '')}
        </motion.div>
      )}

      <InputField
        label={t('Email address')}
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        disabled={isLoading}
        required
      />
      <InputField
        label={t('Password')}
        type="password"
        autoComplete="current-password"
        placeholder={t('Your password')}
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        disabled={isLoading}
        required
      />

      <label className="check-row">
        <input
          type="checkbox"
          checked={rememberMe}
          onChange={(event) => setRememberMe(event.target.checked)}
          disabled={isLoading}
        />
        <span>{t('Remember me on this device')}</span>
      </label>

      <motion.button
        className="button button-primary auth-submit"
        type="submit"
        disabled={isLoading}
        whileTap={{ scale: 0.985 }}
        transition={{ type: 'spring', stiffness: 420, damping: 28 }}
      >
        {isLoading ? t('Signing in…') : t('Sign in')}
        {!isLoading && <span aria-hidden="true">↗</span>}
      </motion.button>

      <p className="form-switch">
        {t('New to Aegis Core?')}{' '}
        <button type="button" onClick={onSwitchToRegister} disabled={isLoading}>
          {t('Create account')}
        </button>
      </p>
    </form>
  );
};
