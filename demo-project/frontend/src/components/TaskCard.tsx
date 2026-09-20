import React from 'react';
import { Task } from '../types';
import { Badge } from './common/Badge';

interface TaskCardProps {
  task: Task;
  onSelect: (task: Task) => void;
  onQuickStatusChange?: (taskId: number, status: Task['status']) => void;
}

export const TaskCard: React.FC<TaskCardProps> = ({
  task,
  onSelect,
  onQuickStatusChange,
}) => {
  return (
    <div
      className="card"
      onClick={() => onSelect(task)}
      style={{
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        gap: '0.75rem',
        padding: '1.25rem',
      }}
    >
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '0.5rem', marginBottom: '0.5rem' }}>
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
            <Badge type="priority" value={task.priority} />
            {task.is_overdue && <Badge type="overdue" value="overdue" />}
          </div>
          <Badge type="status" value={task.status} />
        </div>

        <h3 style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', marginBottom: '0.4rem', lineHeight: '1.4' }}>
          {task.title}
        </h3>

        {task.description && (
          <p
            style={{
              color: 'var(--text-secondary)',
              fontSize: '0.85rem',
              lineHeight: '1.5',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden',
              marginBottom: '0.75rem'
            }}
          >
            {task.description}
          </p>
        )}
      </div>

      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: '0.75rem',
          fontSize: '0.775rem',
          color: 'var(--text-muted)'
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {task.project_name && (
            <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>
              📁 {task.project_name}
            </span>
          )}
          {task.comment_count !== undefined && task.comment_count > 0 && (
            <span>💬 {task.comment_count}</span>
          )}
        </div>

        {onQuickStatusChange && (
          <select
            value={task.status}
            onClick={(e) => e.stopPropagation()}
            onChange={(e) => onQuickStatusChange(task.id, e.target.value as Task['status'])}
            style={{
              background: 'var(--bg-input)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
              color: 'var(--text-primary)',
              fontSize: '0.75rem',
              padding: '0.2rem 0.4rem',
              cursor: 'pointer'
            }}
          >
            <option value="todo">To Do</option>
            <option value="in_progress">In Progress</option>
            <option value="review">Review</option>
            <option value="done">Done</option>
          </select>
        )}
      </div>
    </div>
  );
};
