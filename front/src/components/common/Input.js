import React, { forwardRef } from 'react';
import './Input.css';

const Input = forwardRef(({
  label,
  error,
  hint,
  icon: Icon,
  iconPosition = 'start',
  fullWidth = true,
  className = '',
  type = 'text',
  ...props
}, ref) => {
  const wrapperClass = [
    'input-wrapper',
    fullWidth && 'input-full',
    error && 'input-error',
    Icon && `input-with-icon input-icon-${iconPosition}`,
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={wrapperClass}>
      {label && <label className="input-label">{label}</label>}
      <div className="input-container">
        {Icon && <Icon className="input-icon" />}
        <input
          ref={ref}
          type={type}
          className="input-field"
          {...props}
        />
      </div>
      {error && <span className="input-error-text">{error}</span>}
      {hint && !error && <span className="input-hint">{hint}</span>}
    </div>
  );
});

Input.displayName = 'Input';

export default Input;

