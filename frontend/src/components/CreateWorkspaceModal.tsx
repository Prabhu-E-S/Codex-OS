import React, { useState } from 'react';
import { X, GitBranch, FolderGit2, Info } from 'lucide-react';
import { Project, CreateWorkspacePayload } from '../api/types';

interface CreateWorkspaceModalProps {
  isOpen: boolean;
  project: Project | null;
  onClose: () => void;
  onSubmit: (projectId: number, payload: CreateWorkspacePayload) => Promise<void>;
}

const NAME_REGEX = /^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$/;

export const CreateWorkspaceModal: React.FC<CreateWorkspaceModalProps> = ({
  isOpen,
  project,
  onClose,
  onSubmit,
}) => {
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen || !project) return null;

  const trimmedName = name.trim();
  const isValidName = trimmedName ? NAME_REGEX.test(trimmedName) : false;
  const branchPreview = trimmedName ? `codex/workspace/${trimmedName}` : 'codex/workspace/<name>';

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!trimmedName) {
      setError('Workspace name is required');
      return;
    }

    if (!NAME_REGEX.test(trimmedName)) {
      setError(
        'Workspace name must start with an alphanumeric character and contain only letters, numbers, hyphens, and underscores (max 64 chars).'
      );
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(project.id, {
        name: trimmedName,
      });
      setName('');
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to create workspace');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '520px' }}>
        <div className="modal-header">
          <div className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FolderGit2 size={16} color="#059669" />
            <span>Create Isolated Git Workspace</span>
          </div>
          <button
            className="btn btn-secondary btn-icon-only"
            onClick={onClose}
            aria-label="Close modal"
          >
            <X size={15} />
          </button>
        </div>

        <form onSubmit={handleSubmit}>
          <div className="modal-body">
            {error && (
              <div className="alert-banner alert-banner-error">
                {error}
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Target Project</label>
              <div
                style={{
                  padding: '8px 12px',
                  backgroundColor: '#F8FAFC',
                  border: '1px solid #E2E8F0',
                  borderRadius: '6px',
                  fontSize: '13px',
                  color: '#334155',
                  fontWeight: 500,
                }}
              >
                {project.name}
                <span style={{ color: '#64748B', fontWeight: 400, marginLeft: '8px', fontSize: '12px' }}>
                  ({project.repository_path})
                </span>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">
                Workspace Name <span style={{ color: '#DC2626' }}>*</span>
              </label>
              <input
                type="text"
                className="input-field"
                placeholder="e.g. feat-auth-module, fix-db-pool"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
                disabled={submitting}
              />
              <span className="form-hint">
                Must start with a letter/number and contain only alphanumeric chars, hyphens, and underscores.
              </span>
            </div>

            <div
              style={{
                backgroundColor: '#F8FAFC',
                border: '1px solid #E2E8F0',
                borderRadius: '6px',
                padding: '12px',
                marginTop: '12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
                fontSize: '12px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#0F172A', fontWeight: 500 }}>
                <GitBranch size={14} color="#059669" />
                <span>Isolated Git Branch:</span>
                <code
                  style={{
                    backgroundColor: '#FFFFFF',
                    border: '1px solid #CBD5E1',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    fontFamily: 'JetBrains Mono, monospace',
                    color: '#059669',
                    fontSize: '11px',
                  }}
                >
                  {branchPreview}
                </code>
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px', color: '#64748B', lineHeight: '1.4' }}>
                <Info size={14} style={{ flexShrink: 0, marginTop: '2px' }} />
                <span>
                  Creates a dedicated Git worktree directory linked to this branch. Codex runs targeting this workspace will execute cleanly in isolation without modifying your primary repository files or branch.
                </span>
              </div>
            </div>
          </div>

          <div className="modal-footer">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onClose}
              disabled={submitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={submitting || !isValidName}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <FolderGit2 size={14} />
              <span>{submitting ? 'Creating Worktree...' : 'Create Workspace'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
