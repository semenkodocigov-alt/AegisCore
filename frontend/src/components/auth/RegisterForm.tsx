import React, { useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../../context/AuthContext';
import { InputField } from './InputField';

interface RegisterFormProps {
  onSuccess?: () => void;
  onSwitchToLogin: () => void;
}

export const RegisterForm: React.FC<RegisterFormProps> = ({ onSuccess, onSwitchToLogin }) => {
  const { register, isLoading, error: authError, clearError, rememberMePreference } = useAuth();
  const [nickname, setNickname] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(rememberMePreference);
  const [validationError, setValidationError] = useState<string | null>(null);

  const passwordStrength = useMemo(() => {
    if (!password) return { label: 'Add a password', score: 0 };
    const score = [
      password.length >= 8,
      /[A-Z]/.test(password),
      /[0-9]/.test(password),
      /[^A-Za-z0-9]/.test(password),
    ].filter(Boolean).length;
    return {
      label: ['Needs work', 'Fair', 'Good', 'Strong', 'Strong'][score],
      score,
    };
  }, [password]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    clearError();
    setValidationError(null);
    const normalizedNickname = nickname.trim();
    const normalizedEmail = email.trim();

    if (normalizedNickname.length < 2 || normalizedNickname.length > 32) {
      setValidationError('Nickname must be between 2 and 32 characters.');
      return;
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalizedEmail)) {
      setValidationError('Enter a valid email address.');
      return;
    }
    if (password.length < 8) {
      setValidationError('Use a password with at least 8 characters.');
      return;
    }
    if (password !== confirmPassword) {
      setValidationError('The passwords do not match.');
      return;
    }

    const result = await register({
      nickname: normalizedNickname,
      email: normalizedEmail,
      password,
      rememberMe,
    });
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
          {validationError || authError}
        </motion.div>
      )}

      <InputField
        label="Nickname"
        autoComplete="nickname"
        placeholder="How should we address you?"
        value={nickname}
        onChange={(event) => setNickname(event.target.value)}
        disabled={isLoading}
        minLength={2}
        maxLength={32}
        required
      />
      <InputField
        label="Email address"
        type="email"
        autoComplete="email"
        placeholder="you@example.com"
        value={email}
        onChange={(event) => setEmail(event.target.value)}
        disabled={isLoading}
        required
      />
      <InputField
        label="Password"
        type="password"
        autoComplete="new-password"
        placeholder="At least 8 characters"
        value={password}
        onChange={(event) => setPassword(event.target.value)}
        disabled={isLoading}
        minLength={8}
        required
      />
      <div className="password-meter" aria-live="polite">
        <div className="password-meter-track">
          <span style={{ width: `${passwordStrength.score * 25}%` }} />
        </div>
        <span>{passwordStrength.label}</span>
      </div>
      <InputField
        label="Confirm password"
        type="password"
        autoComplete="new-password"
        placeholder="Enter it once more"
        value={confirmPassword}
        onChange={(event) => setConfirmPassword(event.target.value)}
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
        <span>Remember me on this device</span>
      </label>

      <motion.button
        className="button button-primary auth-submit"
        type="submit"
        disabled={isLoading}
        whileTap={{ scale: 0.985 }}
        transition={{ type: 'spring', stiffness: 420, damping: 28 }}
      >
        {isLoading ? 'Creating account…' : 'Create account'}
        {!isLoading && <span aria-hidden="true">↗</span>}
      </motion.button>

      <p className="form-switch">
        Already have an account?{' '}
        <button type="button" onClick={onSwitchToLogin} disabled={isLoading}>
          Sign in
        </button>
      </p>
    </form>
  );
};
