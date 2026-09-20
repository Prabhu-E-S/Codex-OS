import React from 'react';
import { DashboardStats, Task } from '../types';
import { Badge } from './common/Badge';

interface DashboardViewProps {
  stats: DashboardStats;
  onSelectTask: (task: Task) => void;
  onNavigateTab: (tab: 'projects' | 'tasks') => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  stats,
  onSelectTask,
  onNavigateTab,
}) => {
  return (
    <div>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.875rem', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '0.25rem' }}>
          Workspace Dashboard
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
          Real-time metrics, project velocity, and actionable task alerts across the workspace.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="stats-grid">
        <div className="card stat-card blue">
          <div className="stat-header">
            <span>Total Projects</span>
            <span>📁</span>
          </div>
          <div className="stat-value">{stats.total_projects}</div>
        </div>

        <div className="card stat-card purple">
          <div className="stat-header">
            <span>Total Tasks</span>
            <span>📋</span>
          </div>
          <div className="stat-value">{stats.total_tasks}</div>
        </div>

        <div className="card stat-card emerald">
          <div className="stat-header">
            <span>Completed</span>
            <span>✅</span>
          </div>
          <div className="stat-value">{stats.completed_tasks}</div>
        </div>

        <div className="card stat-card amber">
          <div className="stat-header">
            <span>In Flight (Pending)</span>
            <span>⏳</span>
          </div>
          <div className="stat-value">{stats.pending_tasks}</div>
        </div>

        <div className="card stat-card rose">
          <div className="stat-header">
            <span>Overdue Tasks</span>
            <span>🚨</span>
          </div>
          <div className="stat-value" style={{ color: stats.overdue_tasks > 0 ? '#f87171' : 'var(--text-primary)' }}>
            {stats.overdue_tasks}
          </div>
        </div>
      </div>

      {/* Breakdowns & Recent Activity */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        {/* Status Breakdown */}
        <div className="card">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>Status Distribution</span>
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {Object.entries(stats.tasks_by_status).map(([statusKey, count]) => {
              const total = stats.total_tasks || 1;
              const percent = Math.round((count / total) * 100);
              return (
                <div key={statusKey}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                    <span style={{ textTransform: 'capitalize', color: 'var(--text-secondary)' }}>{statusKey.replace('_', ' ')}</span>
                    <span style={{ fontWeight: 600 }}>{count} ({percent}%)</span>
                  </div>
                  <div style={{ height: '8px', background: 'var(--bg-input)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${percent}%`,
                        height: '100%',
                        borderRadius: 'var(--radius-full)',
                        background:
                          statusKey === 'done' ? 'var(--accent-emerald)' :
                          statusKey === 'in_progress' ? 'var(--accent-blue)' :
                          statusKey === 'review' ? 'var(--accent-purple)' : 'var(--text-muted)'
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Priority Breakdown */}
        <div className="card">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>Priority Breakdown</span>
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {Object.entries(stats.tasks_by_priority).map(([priorityKey, count]) => {
              const total = stats.total_tasks || 1;
              const percent = Math.round((count / total) * 100);
              return (
                <div key={priorityKey}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', marginBottom: '0.35rem' }}>
                    <span style={{ textTransform: 'capitalize', color: 'var(--text-secondary)' }}>{priorityKey} Priority</span>
                    <span style={{ fontWeight: 600 }}>{count} ({percent}%)</span>
                  </div>
                  <div style={{ height: '8px', background: 'var(--bg-input)', borderRadius: 'var(--radius-full)', overflow: 'hidden' }}>
                    <div
                      style={{
                        width: `${percent}%`,
                        height: '100%',
                        borderRadius: 'var(--radius-full)',
                        background:
                          priorityKey === 'urgent' ? 'var(--accent-rose)' :
                          priorityKey === 'high' ? 'var(--accent-amber)' :
                          priorityKey === 'medium' ? 'var(--accent-blue)' : 'var(--text-muted)'
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Recent Tasks */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700 }}>Recently Updated Tasks</h3>
          <button onClick={() => onNavigateTab('tasks')} className="btn btn-ghost" style={{ fontSize: '0.85rem' }}>
            View All Tasks &rarr;
          </button>
        </div>

        {stats.recent_tasks.length === 0 ? (
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem' }}>No tasks found in workspace.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {stats.recent_tasks.map((task) => (
              <div
                key={task.id}
                onClick={() => onSelectTask(task)}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '0.85rem 1rem',
                  background: 'var(--bg-card-hover)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-md)',
                  cursor: 'pointer',
                  transition: 'var(--transition)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', minWidth: 0 }}>
                  <Badge type="priority" value={task.priority} />
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.925rem', color: 'var(--text-primary)' }}>
                      {task.title}
                    </span>
                    {task.project_name && (
                      <span style={{ marginLeft: '0.65rem', fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
                        • {task.project_name}
                      </span>
                    )}
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
                  {task.is_overdue && <Badge type="overdue" value="overdue" />}
                  <Badge type="status" value={task.status} />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
