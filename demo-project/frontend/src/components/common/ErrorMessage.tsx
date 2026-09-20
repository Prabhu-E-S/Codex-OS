import React from 'react';

interface ErrorMessageProps {
  message: string;
  onRetry?: () => void;
}

export const ErrorMessage: React.FC<ErrorMessageProps> = ({ message, onRetry }) => {
  return (
    <div
      style={{
        background: 'rgba(239, 68, 68, 0.12)',
        border: '1px solid rgba(239, 68, 68, 0.3)',
        borderRadius: 'var(--radius-lg)',
        padding: '1.5rem',
        margin: '1.5rem 0',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <span style={{ fontSize: '1.5rem' }}>⚠️</span>
        <div>
          <h4 style={{ color: '#fca5a5', fontWeight: 600, fontSize: '0.95rem' }}>An error occurred</h4>
          <p style={{ color: '#f87171', fontSize: '0.875rem' }}>{message}</p>
        </div>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="btn btn-secondary"
          style={{ fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}
        >
          Retry
        </button>
      )}
    </div>
  );
};
