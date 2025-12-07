import React from 'react';
import './Loading.css';

export const Spinner = ({ size = 'medium', className = '' }) => (
  <div className={`spinner spinner-${size} ${className}`} />
);

export const LoadingScreen = ({ message = 'در حال بارگذاری...' }) => (
  <div className="loading-screen">
    <div className="loading-content">
      <Spinner size="large" />
      <p className="loading-message">{message}</p>
    </div>
  </div>
);

export const LoadingOverlay = ({ message }) => (
  <div className="loading-overlay">
    <div className="loading-content">
      <Spinner size="large" />
      {message && <p className="loading-message">{message}</p>}
    </div>
  </div>
);

export const Skeleton = ({ width, height, radius = 'medium', className = '' }) => (
  <div 
    className={`skeleton skeleton-radius-${radius} ${className}`}
    style={{ width, height }}
  />
);

export const SkeletonText = ({ lines = 3, className = '' }) => (
  <div className={`skeleton-text ${className}`}>
    {Array.from({ length: lines }).map((_, i) => (
      <Skeleton 
        key={i} 
        height="1rem" 
        width={i === lines - 1 ? '60%' : '100%'} 
      />
    ))}
  </div>
);

export default Spinner;

