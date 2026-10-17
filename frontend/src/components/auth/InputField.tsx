import React, { useId, useState } from 'react';

interface InputFieldProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string | null;
  hint?: string;
}

export const InputField: React.FC<InputFieldProps> = ({
  label,
  error,
  hint,
  type = 'text',
  className = '',
  id,
  ...props
}) => {
  const generatedId = useId();
  const inputId = id || generatedId;
  const [showPassword, setShowPassword] = useState(false);
  const isPassword = type === 'password';

  return (
    <div className="field">
      <label className="field-label" htmlFor={inputId}>{label}</label>
      <div className="field-control-wrap">
        <input
          {...props}
          id={inputId}
          type={isPassword && showPassword ? 'text' : type}
          aria-invalid={Boolean(error)}
          aria-describedby={error ? `${inputId}-error` : hint ? `${inputId}-hint` : undefined}
          className={`field-control ${error ? 'field-control-error' : ''} ${isPassword ? 'field-control-password' : ''} ${className}`}
        />
        {isPassword && (
          <button
            className="field-reveal"
            type="button"
            onClick={() => setShowPassword((value) => !value)}
            aria-label={showPassword ? 'Hide password' : 'Show password'}
          >
            {showPassword ? 'Hide' : 'Show'}
          </button>
        )}
      </div>
      {error && <p className="field-message field-message-error" id={`${inputId}-error`}>{error}</p>}
      {!error && hint && <p className="field-message" id={`${inputId}-hint`}>{hint}</p>}
    </div>
  );
};
