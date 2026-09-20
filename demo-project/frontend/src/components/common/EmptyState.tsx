import React from 'react';

interface EmptyStateProps {
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  icon?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title,
  description,
  actionText,
  onAction,
  icon = '📋'
}) => {
  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '4rem 2rem',
        textAlign: 'center',
        background: 'var(--bg-glass)',
        border: '1px dashed var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        margin: '1.5rem 0',
      }}
    >
      <div style={{ fontSize: '3rem', marginBottom: '1rem', filter: 'grayscale(0.3)' }}>{icon}</div>
      <h3 style={{ fontSize: '1.15rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '0.4rem' }}>
        {title}
      </h3>
      <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', maxWidth: '400px', marginBottom: actionText ? '1.5rem' : '0' }}>
        {description}
      </p>
      {actionText && onAction && (
        <button onClick={onAction} className="btn btn-primary">
          {actionText}
        </button>
      )}
    </div>
  );
};
