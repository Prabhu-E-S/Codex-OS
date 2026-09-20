import React, { useState } from 'react';
import { Project } from '../types';
import { Button } from './common/Button';

interface ProjectDetailModalProps {
  project: Project;
  onClose: () => void;
  onUpdateProject: (id: number, data: Partial<Project>) => Promise<void>;
  onDeleteProject: (id: number) => Promise<void>;
  onViewTasksForProject: (projectId: number) => void;
}

export const ProjectDetailModal: React.FC<ProjectDetailModalProps> = ({
  project,
  onClose,
  onUpdateProject,
  onDeleteProject,
  onViewTasksForProject,
}) => {
  const [status, setStatus] = useState(project.status);
  const [isUpdating, setIsUpdating] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);

  const handleStatusChange = async (newStatus: 'active' | 'completed' | 'archived') => {
    try {
      setIsUpdating(true);
      setStatus(newStatus);
      await onUpdateProject(project.id, { status: newStatus });
    } finally {
      setIsUpdating(false);
    }
  };

  const handleDelete = async () => {
    if (window.confirm(`Are you sure you want to delete project "${project.name}" and all its tasks?`)) {
      try {
        setIsDeleting(true);
        await onDeleteProject(project.id);
        onClose();
      } finally {
        setIsDeleting(false);
      }
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Project Details
            </span>
            <h2 className="modal-title">{project.name}</h2>
          </div>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <div style={{ marginBottom: '1.5rem' }}>
          <h4 style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.35rem' }}>Description</h4>
          <p style={{ color: 'var(--text-primary)', fontSize: '0.95rem', lineHeight: '1.6' }}>
            {project.description || 'No detailed description provided.'}
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
          <div style={{ background: 'var(--bg-input)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Status</span>
            <select
              value={status}
              disabled={isUpdating}
              onChange={(e) => handleStatusChange(e.target.value as 'active' | 'completed' | 'archived')}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-primary)',
                fontWeight: 600,
                fontSize: '0.9rem',
                cursor: 'pointer',
                outline: 'none',
                marginTop: '0.2rem'
              }}
            >
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="archived">Archived</option>
            </select>
          </div>

          <div style={{ background: 'var(--bg-input)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Associated Tasks</span>
            <span style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--text-primary)', display: 'block', marginTop: '0.2rem' }}>
              {project.task_count ?? 0}
            </span>
          </div>
        </div>

        {project.owner && (
          <div style={{ marginBottom: '1.5rem', background: 'var(--bg-card)', padding: '0.75rem 1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Owner</span>
            <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>{project.owner.full_name}</span>
            <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginLeft: '0.5rem' }}>({project.owner.email})</span>
          </div>
        )}

        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '2rem', borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
          <Button variant="danger" isLoading={isDeleting} onClick={handleDelete}>
            Delete Project
          </Button>

          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
            <Button onClick={() => { onClose(); onViewTasksForProject(project.id); }}>
              View Tasks &rarr;
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
