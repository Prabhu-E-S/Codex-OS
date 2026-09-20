import React, { useState } from 'react';
import { Project, User } from '../types';
import { Button } from './common/Button';
import { EmptyState } from './common/EmptyState';

interface ProjectListProps {
  projects: Project[];
  users: User[];
  onSelectProject: (project: Project) => void;
  onCreateProject: (data: { name: string; description?: string; status?: string; owner_id: number }) => Promise<void>;
}

export const ProjectList: React.FC<ProjectListProps> = ({
  projects,
  users,
  onSelectProject,
  onCreateProject,
}) => {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [status, setStatus] = useState('active');
  const [ownerId, setOwnerId] = useState<number | ''>(users[0]?.id || '');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      setError('Project name is required');
      return;
    }
    if (!ownerId) {
      setError('Project owner is required');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onCreateProject({
        name: name.trim(),
        description: description.trim() || undefined,
        status,
        owner_id: Number(ownerId),
      });
      setName('');
      setDescription('');
      setShowCreateModal(false);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create project');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '0.25rem' }}>
            Projects
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            Track engineering initiatives, milestones, and deliverable associations.
          </p>
        </div>
        <Button onClick={() => setShowCreateModal(true)}>
          + New Project
        </Button>
      </div>

      {projects.length === 0 ? (
        <EmptyState
          title="No Projects Yet"
          description="Create your first project to start organizing tasks and tracking progress."
          actionText="Create Project"
          onAction={() => setShowCreateModal(true)}
          icon="📁"
        />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', gap: '1.25rem' }}>
          {projects.map((project) => (
            <div
              key={project.id}
              className="card"
              onClick={() => onSelectProject(project)}
              style={{
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                justifyContent: 'space-between',
                height: '100%',
              }}
            >
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
                  <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                    {project.name}
                  </h3>
                  <span
                    className={`badge ${
                      project.status === 'completed' ? 'badge-done' :
                      project.status === 'archived' ? 'badge-low' : 'badge-in_progress'
                    }`}
                  >
                    {project.status}
                  </span>
                </div>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem', lineHeight: '1.5', marginBottom: '1.25rem' }}>
                  {project.description || 'No description provided.'}
                </p>
              </div>

              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  borderTop: '1px solid var(--border-subtle)',
                  paddingTop: '0.85rem',
                  fontSize: '0.825rem',
                  color: 'var(--text-muted)'
                }}
              >
                <span>Tasks: <strong style={{ color: 'var(--text-primary)' }}>{project.task_count ?? 0}</strong></span>
                <span style={{ color: 'var(--accent-blue)', fontWeight: 500 }}>View Details &rarr;</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Create Project Modal */}
      {showCreateModal && (
        <div className="modal-backdrop" onClick={() => setShowCreateModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h2 className="modal-title">Create New Project</h2>
              <button className="close-btn" onClick={() => setShowCreateModal(false)}>&times;</button>
            </div>

            {error && (
              <div style={{ color: '#f87171', background: 'rgba(239, 68, 68, 0.1)', padding: '0.75rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', fontSize: '0.875rem' }}>
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label className="form-label">Project Name *</label>
                <input
                  type="text"
                  className="form-input"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Infrastructure Modernization"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Description</label>
                <textarea
                  className="form-textarea"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Goals, deliverables, and scope..."
                />
              </div>

              <div className="form-group">
                <label className="form-label">Initial Status</label>
                <select className="form-select" value={status} onChange={(e) => setStatus(e.target.value)}>
                  <option value="active">Active</option>
                  <option value="completed">Completed</option>
                  <option value="archived">Archived</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Project Owner *</label>
                <select
                  className="form-select"
                  value={ownerId}
                  onChange={(e) => setOwnerId(e.target.value ? Number(e.target.value) : '')}
                  required
                >
                  <option value="" disabled>Select Owner</option>
                  {users.map((u) => (
                    <option key={u.id} value={u.id}>{u.full_name} ({u.email})</option>
                  ))}
                </select>
              </div>

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
                <Button type="button" variant="secondary" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </Button>
                <Button type="submit" isLoading={isSubmitting}>
                  Create Project
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
