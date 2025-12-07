import React from 'react';
import './Badge.css';

const Badge = ({ 
  children, 
  variant = 'default', 
  size = 'medium',
  dot = false,
  className = '' 
}) => {
  const classNames = [
    'badge',
    `badge-${variant}`,
    `badge-${size}`,
    dot && 'badge-dot',
    className,
  ].filter(Boolean).join(' ');

  return (
    <span className={classNames}>
      {dot && <span className="badge-dot-indicator" />}
      {children}
    </span>
  );
};

export default Badge;

