import React from 'react';

interface BadgeProps {
  type: 'status' | 'priority' | 'overdue' | 'role';
  value: string;
}

export const Badge: React.FC<BadgeProps> = ({ type, value }) => {
  let className = 'badge ';

  if (type === 'overdue') {
    return <span className="badge badge-overdue">⚠️ Overdue</span>;
  }

  if (type === 'status') {
    className += `badge-${value.toLowerCase()}`;
    const labels: Record<string, string> = {
      todo: 'To Do',
      in_progress: 'In Progress',
      review: 'Review',
      done: 'Completed'
    };
    return <span className={className}>{labels[value] || value}</span>;
  }

  if (type === 'priority') {
    className += `badge-${value.toLowerCase()}`;
    const labels: Record<string, string> = {
      low: 'Low',
      medium: 'Medium',
      high: 'High',
      urgent: 'Urgent'
    };
    return <span className={className}>{labels[value] || value}</span>;
  }

  return <span className="badge badge-low">{value}</span>;
};
