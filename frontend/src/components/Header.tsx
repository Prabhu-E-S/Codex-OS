import React from 'react';
import { Terminal, Plus, FolderKanban, Menu, X } from 'lucide-react';
import { Project } from '../api/types';

interface HeaderProps {
  projects: Project[];
  selectedProjectId: number | null;
  onSelectProject: (id: number) => void;
  onOpenCreateProject: () => void;
  mobileMenuOpen: boolean;
  onToggleMobileMenu: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  projects,
  selectedProjectId,
  onSelectProject,
  onOpenCreateProject,
  mobileMenuOpen,
  onToggleMobileMenu,
}) => {
  return (
    <header className="top-header">
      <div className="header-left">
        <button
          className="btn btn-secondary btn-icon-only mobile-menu-btn"
          onClick={onToggleMobileMenu}
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
        </button>

        <div className="logo-container">
          <Terminal size={18} strokeWidth={2.2} color="#242424" />
          <span>Codex OS</span>
          <span className="logo-badge">v0.1.0 • Phase 1</span>
        </div>
      </div>

      <div className="header-right">
        {projects.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FolderKanban size={15} color="#6B6B67" />
            <select
              className="form-select"
              style={{ padding: '5px 8px', fontSize: '12.5px', height: '32px' }}
              value={selectedProjectId ?? ''}
              onChange={(e) => onSelectProject(Number(e.target.value))}
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id}>
                  Project: {p.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <button
          className="btn btn-primary btn-sm"
          onClick={onOpenCreateProject}
          id="btn-create-project-header"
        >
          <Plus size={14} />
          <span>New Project</span>
        </button>
      </div>
    </header>
  );
};
