import React, { useState, useEffect } from 'react';
import { X, PlayCircle, FolderGit2 } from 'lucide-react';
import { CreateRunPayload, Project, Workspace } from '../api/types';
import { api } from '../api/client';

interface CreateRunModalProps {
  isOpen: boolean;
  project: Project | null;
  onClose: () => void;
  onSubmit: (projectId: number, payload: CreateRunPayload) => Promise<void>;
}

export const CreateRunModal: React.FC<CreateRunModalProps> = ({
  isOpen,
  project,
  onClose,
  onSubmit,
}) => {
  const [goal, setGoal] = useState('');
  const [status, setStatus] = useState('PENDING');
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState<string>('');
  const [loadingWorkspaces, setLoadingWorkspaces] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (isOpen && project) {
      setLoadingWorkspaces(true);
      api
        .getProjectWorkspaces(project.id)
        .then((wsList) => {
          setWorkspaces(wsList.filter((w) => w.status !== 'REMOVED'));
        })
        .catch(() => setWorkspaces([]))
        .finally(() => setLoadingWorkspaces(false));
    } else {
      setSelectedWorkspaceId('');
      setWorkspaces([]);
    }
  }, [isOpen, project]);

  if (!isOpen || !project) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!goal.trim()) {
      setError('Engineering goal is required');
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await onSubmit(project.id, {
        goal: goal.trim(),
        status,
        workspace_id: selectedWorkspaceId ? parseInt(selectedWorkspaceId, 10) : undefined,
      });
      setGoal('');
      setStatus('PENDING');
      setSelectedWorkspaceId('');
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to create engineering run');
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <PlayCircle size={16} color="#2563EB" />
            <span>New Engineering Run</span>
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
              <label className="form-label">
                Target Project
              </label>
              <div className="mono-path" style={{ width: '100%', padding: '6px 10px' }}>
                {project.name} ({project.repository_path})
              </div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="run-workspace" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <FolderGit2 size={14} color="#059669" />
                <span>Isolated Workspace (Git Worktree)</span>
              </label>
              <select
                id="run-workspace"
                className="form-select"
                value={selectedWorkspaceId}
                onChange={(e) => setSelectedWorkspaceId(e.target.value)}
                disabled={loadingWorkspaces}
              >
                <option value="">None (Execute in primary repository path)</option>
                {workspaces.map((ws) => (
                  <option key={ws.id} value={ws.id}>
                    {ws.name} ({ws.branch_name}) [{ws.status}]
                  </option>
                ))}
              </select>
              <span className="form-help">
                Optional. Select an isolated Git worktree to execute changes safely on a dedicated branch without mutating primary files.
              </span>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="run-goal">
                Engineering Goal / Task <span className="form-required">*</span>
              </label>
              <textarea
                id="run-goal"
                rows={3}
                className="form-textarea"
                placeholder="e.g. Implement user authentication middleware and verify with pytest"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                autoFocus
              />
              <span className="form-help">
                State the target engineering objective for this run record.
              </span>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="run-status">
                Initial Status
              </label>
              <select
                id="run-status"
                className="form-select"
                value={status}
                onChange={(e) => setStatus(e.target.value)}
              >
                <option value="PENDING">PENDING</option>
                <option value="INITIALIZED">INITIALIZED</option>
              </select>
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
              disabled={submitting}
              id="submit-create-run"
            >
              {submitting ? 'Recording...' : 'Record Run'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
