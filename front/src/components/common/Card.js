import React from 'react';
import './Card.css';

export const Card = ({ children, className = '', padding = 'medium', hover = false, ...props }) => {
  const classNames = [
    'card',
    `card-padding-${padding}`,
    hover && 'card-hover',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div className={classNames} {...props}>
      {children}
    </div>
  );
};

export const CardHeader = ({ children, className = '', action, ...props }) => (
  <div className={`card-header ${className}`} {...props}>
    <div className="card-header-content">{children}</div>
    {action && <div className="card-header-action">{action}</div>}
  </div>
);

export const CardTitle = ({ children, className = '', ...props }) => (
  <h3 className={`card-title ${className}`} {...props}>{children}</h3>
);

export const CardDescription = ({ children, className = '', ...props }) => (
  <p className={`card-description ${className}`} {...props}>{children}</p>
);

export const CardContent = ({ children, className = '', ...props }) => (
  <div className={`card-content ${className}`} {...props}>{children}</div>
);

export const CardFooter = ({ children, className = '', ...props }) => (
  <div className={`card-footer ${className}`} {...props}>{children}</div>
);

export default Card;

