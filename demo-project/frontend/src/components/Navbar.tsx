import React from 'react';

interface NavbarProps {
  activeTab: 'dashboard' | 'projects' | 'tasks';
  onSelectTab: (tab: 'dashboard' | 'projects' | 'tasks') => void;
  onOpenCreateTask: () => void;
  isBackendConnected: boolean;
}

export const Navbar: React.FC<NavbarProps> = ({
  activeTab,
  onSelectTab,
  onOpenCreateTask,
  isBackendConnected,
}) => {
  return (
    <nav className="navbar">
      <div className="navbar-inner">
        <div style={{ display: 'flex', alignItems: 'center', gap: '2rem' }}>
          <a href="#" onClick={(e) => { e.preventDefault(); onSelectTab('dashboard'); }} className="brand">
            <div className="brand-icon">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <polygon points="12 2 2 7 12 12 22 7 12 2"></polygon>
                <polyline points="2 17 12 22 22 17"></polyline>
                <polyline points="2 12 12 17 22 12"></polyline>
              </svg>
            </div>
            <span>TaskForge</span>
          </a>

          <div className="nav-links">
            <button
              className={`nav-link ${activeTab === 'dashboard' ? 'active' : ''}`}
              onClick={() => onSelectTab('dashboard')}
            >
              Dashboard
            </button>
            <button
              className={`nav-link ${activeTab === 'projects' ? 'active' : ''}`}
              onClick={() => onSelectTab('projects')}
            >
              Projects
            </button>
            <button
              className={`nav-link ${activeTab === 'tasks' ? 'active' : ''}`}
              onClick={() => onSelectTab('tasks')}
            >
              Tasks
            </button>
          </div>
        </div>

        <div className="nav-actions">
          <div className="health-pill" title={isBackendConnected ? "API Connected" : "API Offline"}>
            <span
              className="health-dot"
              style={{
                backgroundColor: isBackendConnected ? 'var(--accent-emerald)' : 'var(--accent-rose)',
                boxShadow: isBackendConnected ? '0 0 6px var(--accent-emerald)' : '0 0 6px var(--accent-rose)'
              }}
            />
            <span>{isBackendConnected ? 'API Online' : 'API Offline'}</span>
          </div>

          <button onClick={onOpenCreateTask} className="btn btn-primary">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
            New Task
          </button>
        </div>
      </div>
    </nav>
  );
};
