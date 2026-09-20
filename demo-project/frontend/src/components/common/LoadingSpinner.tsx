import React from 'react';

export const LoadingSpinner: React.FC<{ message?: string }> = ({ message = 'Loading TaskForge data...' }) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '4rem 2rem', gap: '1rem' }}>
      <svg
        style={{ width: '2.5rem', height: '2.5rem', animation: 'spin 1s linear infinite', color: 'var(--accent-blue)' }}
        xmlns="http://www.w3.org/2000/svg"
        fill="none"
        viewBox="0 0 24 24"
      >
        <circle
          style={{ opacity: 0.2 }}
          cx="12"
          cy="12"
          r="10"
          stroke="currentColor"
          strokeWidth="3"
        />
        <path
          style={{ opacity: 0.9 }}
          fill="currentColor"
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
        />
      </svg>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', fontWeight: 500 }}>{message}</p>
    </div>
  );
};
