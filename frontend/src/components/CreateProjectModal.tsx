import React, { useState } from 'react';
import { X, FolderGit2 } from 'lucide-react';
import { CreateProjectPayload } from '../api/types';

interface CreateProjectModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (payload: CreateProjectPayload) => Promise<void>;
}

export const CreateProjectModal: React.FC<CreateProjectModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
}) => {
  const [name, setName] = useState('');
  const [repositoryPath, setRepositoryPath] = useState('');
  const [description, setDescription] = useState('');
  const [errors, setErrors] = useState<{ name?: string; repositoryPath?: string; general?: string }>({});
  const [submitting, setSubmitting] = useState(false);

  if (!isOpen) return null;

  const validate = () => {
    const errs: { name?: string; repositoryPath?: string } = {};
    if (!name.trim()) {
      errs.name = 'Project name is required';
    }
    if (!repositoryPath.trim()) {
      errs.repositoryPath = 'Repository path is required';
    }
    setErrors(errs);
    return Object.keys(errs).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;

    setSubmitting(true);
    setErrors({});
    try {
      await onSubmit({
        name: name.trim(),
        repository_path: repositoryPath.trim(),
        description: description.trim() || undefined,
      });
      // Clear form on success
      setName('');
      setRepositoryPath('');
      setDescription('');
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setErrors({ general: err.message });
      } else {
        setErrors({ general: 'Failed to create project' });
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
            <FolderGit2 size={16} color="#2563EB" />
            <span>Create New Project</span>
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
            {errors.general && (
              <div className="alert-banner alert-banner-error">
                {errors.general}
              </div>
            )}

            <div className="form-group">
              <label className="form-label" htmlFor="project-name">
                Project Name <span className="form-required">*</span>
              </label>
              <input
                id="project-name"
                type="text"
                className={`form-input ${errors.name ? 'error' : ''}`}
                placeholder="e.g. Dataset AI Explorer"
                value={name}
                onChange={(e) => setName(e.target.value)}
                autoFocus
              />
              {errors.name ? (
                <span className="form-error">{errors.name}</span>
              ) : (
                <span className="form-help">A concise developer-friendly name for this workspace.</span>
              )}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="repo-path">
                Repository Path <span className="form-required">*</span>
              </label>
              <input
                id="repo-path"
                type="text"
                className={`form-input ${errors.repositoryPath ? 'error' : ''}`}
                placeholder="e.g. D:\Projects\Dataset-AI-Explorer"
                value={repositoryPath}
                onChange={(e) => setRepositoryPath(e.target.value)}
              />
              {errors.repositoryPath ? (
                <span className="form-error">{errors.repositoryPath}</span>
              ) : (
                <span className="form-help">Local absolute path to the project directory or git repository.</span>
              )}
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="project-desc">
                Description <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(optional)</span>
              </label>
              <textarea
                id="project-desc"
                rows={3}
                className="form-textarea"
                placeholder="e.g. AI-powered dataset analysis application"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
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
              id="submit-create-project"
            >
              {submitting ? 'Creating...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
