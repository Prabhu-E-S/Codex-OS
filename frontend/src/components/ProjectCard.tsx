import React from 'react';
import { FolderGit2, Trash2, Calendar, HardDrive, CheckCircle2 } from 'lucide-react';
import { Project } from '../api/types';

interface ProjectCardProps {
  project: Project | null;
  onDeleteProject: (id: number) => void;
  onOpenCreateProject: () => void;
}

export const ProjectCard: React.FC<ProjectCardProps> = ({
  project,
  onDeleteProject,
  onOpenCreateProject,
}) => {
  if (!project) {
    return (
      <div className="card-panel">
        <div className="card-header">
          <div className="card-title">
            <FolderGit2 size={15} color="#242424" />
            <span>Active Project</span>
          </div>
        </div>
        <div className="empty-state">
          <div className="empty-icon">
            <FolderGit2 size={20} />
          </div>
          <div className="empty-title">No Project Configured</div>
          <div className="empty-desc">
            Codex OS requires a target project repository to inspect codebase architecture and anchor engineering runs.
          </div>
          <button
            className="btn btn-primary btn-sm"
            onClick={onOpenCreateProject}
            style={{ marginTop: '8px' }}
          >
            Create First Project
          </button>
        </div>
      </div>
    );
  }

  const formattedDate = new Date(project.created_at).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <div className="card-panel">
      <div className="card-header">
        <div className="card-title">
          <FolderGit2 size={15} color="#242424" />
          <span>Project Details</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-success">
            <CheckCircle2 size={11} /> {project.status}
          </span>
          <button
            className="btn btn-danger btn-sm"
            onClick={() => {
              if (window.confirm(`Are you sure you want to delete project "${project.name}"?`)) {
                onDeleteProject(project.id);
              }
            }}
            title="Delete this project"
            aria-label="Delete project"
          >
            <Trash2 size={13} />
            <span>Delete</span>
          </button>
        </div>
      </div>

      <div className="card-body">
        <div className="info-list">
          <div className="info-item">
            <span className="info-item-label">Project Name</span>
            <span className="info-item-value" style={{ fontSize: '15px', fontWeight: 600 }}>
              {project.name}
            </span>
          </div>

          <div className="info-item">
            <span className="info-item-label">Repository Path</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
              <HardDrive size={13} color="#6B6B67" />
              <span className="mono-path">{project.repository_path}</span>
            </div>
          </div>

          {project.description && (
            <div className="info-item">
              <span className="info-item-label">Description</span>
              <span className="info-item-value" style={{ color: 'var(--text-secondary)' }}>
                {project.description}
              </span>
            </div>
          )}

          <div className="info-item">
            <span className="info-item-label">Created Date</span>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)' }}>
              <Calendar size={13} />
              <span>{formattedDate}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
