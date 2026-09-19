import React, { useState, useEffect, useCallback } from 'react';
import {
  FolderGit2,
  GitBranch,
  Plus,
  RefreshCw,
  HardDrive,
  Trash2,
  ExternalLink,
  AlertCircle,
  Clock,
  ShieldCheck,
} from 'lucide-react';
import { Project, Workspace, CreateWorkspacePayload } from '../api/types';
import { api } from '../api/client';
import { CreateWorkspaceModal } from '../components/CreateWorkspaceModal';
import { WorkspaceDetailModal } from '../components/WorkspaceDetailModal';

interface WorkspacesViewProps {
  currentProject: Project | null;
}

export const WorkspacesView: React.FC<WorkspacesViewProps> = ({ currentProject }) => {
  const [workspaces, setWorkspaces] = useState<Workspace[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [selectedWorkspace, setSelectedWorkspace] = useState<Workspace | null>(null);
  const [isDetailModalOpen, setIsDetailModalOpen] = useState(false);

  const fetchWorkspaces = useCallback(async () => {
    if (!currentProject) {
      setWorkspaces([]);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const data = await api.getProjectWorkspaces(currentProject.id);
      setWorkspaces(data);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to fetch workspaces');
      }
    } finally {
      setLoading(false);
    }
  }, [currentProject]);

  useEffect(() => {
    fetchWorkspaces();
  }, [fetchWorkspaces]);

  const handleCreateWorkspace = async (projectId: number, payload: CreateWorkspacePayload) => {
    const newWs = await api.createWorkspace(projectId, payload);
    await fetchWorkspaces();
    setSelectedWorkspace(newWs);
    setIsDetailModalOpen(true);
  };

  const handleWorkspaceDeleted = (deletedId: number) => {
    setWorkspaces((prev) => prev.filter((w) => w.id !== deletedId));
  };

  const handleQuickDelete = async (ws: Workspace, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`Are you sure you want to remove workspace "${ws.name}"?`)) return;
    try {
      await api.deleteWorkspace(ws.id);
      handleWorkspaceDeleted(ws.id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to delete workspace');
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'READY':
        return { label: 'Ready', bg: '#ECFDF5', color: '#059669', border: '#A7F3D0' };
      case 'IN_USE':
        return { label: 'In Use', bg: '#EFF6FF', color: '#2563EB', border: '#BFDBFE' };
      case 'CREATING':
        return { label: 'Creating', bg: '#FFFBEB', color: '#D97706', border: '#FDE68A' };
      case 'ERROR':
        return { label: 'Error', bg: '#FEF2F2', color: '#DC2626', border: '#FECACA' };
      case 'REMOVING':
        return { label: 'Removing', bg: '#F5F3FF', color: '#7C3AED', border: '#DDD6FE' };
      case 'REMOVED':
        return { label: 'Removed', bg: '#F1F5F9', color: '#64748B', border: '#CBD5E1' };
      default:
        return { label: status, bg: '#F8FAFC', color: '#475569', border: '#E2E8F0' };
    }
  };

  if (!currentProject) {
    return (
      <div className="empty-state" style={{ padding: '64px 20px', textAlign: 'center' }}>
        <FolderGit2 size={40} color="#94A3B8" style={{ marginBottom: '16px' }} />
        <h2 style={{ fontSize: '18px', color: '#0F172A', marginBottom: '8px' }}>No Active Project Selected</h2>
        <p style={{ color: '#64748B', maxWidth: '440px', margin: '0 auto', fontSize: '13px' }}>
          Please select or create a project from the header above to manage its isolated Git worktree workspaces.
        </p>
      </div>
    );
  }

  return (
    <div>
      {/* View Header */}
      <div className="content-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 className="content-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FolderGit2 size={22} color="#059669" />
            <span>Git Worktree Workspaces</span>
          </h1>
          <p className="content-subtitle">
            Isolated branch and directory workspaces. Codex runs target these worktrees without mutating your main repository.
          </p>
        </div>

        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <button
            className="btn btn-secondary btn-icon-only"
            onClick={fetchWorkspaces}
            disabled={loading}
            title="Refresh workspaces"
          >
            <RefreshCw size={14} className={loading ? 'spin-animation' : ''} />
          </button>

          <button
            className="btn btn-primary"
            onClick={() => setIsCreateModalOpen(true)}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={15} />
            <span>New Workspace</span>
          </button>
        </div>
      </div>

      {/* Project info pill banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '10px 16px',
          backgroundColor: '#F8FAFC',
          border: '1px solid #E2E8F0',
          borderRadius: '8px',
          marginBottom: '20px',
          fontSize: '13px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ color: '#64748B', fontWeight: 500 }}>Active Project:</span>
          <strong style={{ color: '#0F172A' }}>{currentProject.name}</strong>
          <span style={{ color: '#94A3B8' }}>•</span>
          <span style={{ color: '#475569', fontFamily: 'JetBrains Mono, monospace', fontSize: '12px' }}>
            {currentProject.repository_path}
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: '#059669', fontSize: '12px', fontWeight: 500 }}>
          <ShieldCheck size={14} />
          <span>Worktree Isolation Active</span>
        </div>
      </div>

      {error && (
        <div className="alert-banner alert-banner-error" style={{ marginBottom: '20px' }}>
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      )}

      {/* Content */}
      {loading && workspaces.length === 0 ? (
        <div className="empty-state" style={{ padding: '48px' }}>
          <div className="empty-desc">Loading worktree workspaces...</div>
        </div>
      ) : workspaces.length === 0 ? (
        <div
          className="empty-state"
          style={{
            padding: '56px 24px',
            backgroundColor: '#FFFFFF',
            border: '1px dashed #CBD5E1',
            borderRadius: '8px',
            textAlign: 'center',
          }}
        >
          <FolderGit2 size={44} color="#94A3B8" style={{ marginBottom: '16px' }} />
          <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#0F172A', marginBottom: '6px' }}>
            No Workspaces Created Yet
          </h2>
          <p
            style={{
              color: '#64748B',
              fontSize: '13px',
              maxWidth: '460px',
              margin: '0 auto 20px auto',
              lineHeight: '1.5',
            }}
          >
            Create an isolated Git worktree workspace to let Codex execute changes on a clean, dedicated branch and directory without touching your main working files.
          </p>
          <button
            className="btn btn-primary"
            onClick={() => setIsCreateModalOpen(true)}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={15} />
            <span>Create First Workspace</span>
          </button>
        </div>
      ) : (
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))',
            gap: '16px',
          }}
        >
          {workspaces.map((ws) => {
            const badge = getStatusBadge(ws.status);
            return (
              <div
                key={ws.id}
                onClick={() => {
                  setSelectedWorkspace(ws);
                  setIsDetailModalOpen(true);
                }}
                style={{
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #E2E8F0',
                  borderRadius: '8px',
                  padding: '16px',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = '#CBD5E1';
                  e.currentTarget.style.boxShadow = '0 2px 8px rgba(0, 0, 0, 0.04)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = '#E2E8F0';
                  e.currentTarget.style.boxShadow = 'none';
                }}
              >
                {/* Card Header */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                    <FolderGit2 size={16} color="#059669" style={{ flexShrink: 0 }} />
                    <strong
                      style={{
                        fontSize: '14px',
                        color: '#0F172A',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {ws.name}
                    </strong>
                  </div>

                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '9999px',
                      backgroundColor: badge.bg,
                      color: badge.color,
                      border: `1px solid ${badge.border}`,
                      flexShrink: 0,
                    }}
                  >
                    {badge.label}
                  </span>
                </div>

                {/* Branch Info */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '12px',
                    color: '#475569',
                    backgroundColor: '#F8FAFC',
                    padding: '6px 8px',
                    borderRadius: '4px',
                    border: '1px solid #F1F5F9',
                  }}
                >
                  <GitBranch size={13} color="#059669" style={{ flexShrink: 0 }} />
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      fontSize: '11px',
                    }}
                  >
                    {ws.branch_name}
                  </span>
                </div>

                {/* Path info */}
                <div
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                    fontSize: '11px',
                    color: '#64748B',
                  }}
                >
                  <HardDrive size={13} style={{ flexShrink: 0 }} />
                  <span
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {ws.path}
                  </span>
                </div>

                {/* Footer info & quick actions */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    paddingTop: '8px',
                    borderTop: '1px solid #F1F5F9',
                    marginTop: 'auto',
                    fontSize: '11px',
                    color: '#94A3B8',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <Clock size={11} />
                    <span>{new Date(ws.created_at).toLocaleDateString()}</span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <button
                      className="btn btn-secondary btn-icon-only"
                      style={{ padding: '4px', height: '24px', width: '24px', color: '#64748B' }}
                      title="Inspect workspace"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSelectedWorkspace(ws);
                        setIsDetailModalOpen(true);
                      }}
                    >
                      <ExternalLink size={12} />
                    </button>

                    <button
                      className="btn btn-secondary btn-icon-only"
                      style={{ padding: '4px', height: '24px', width: '24px', color: '#DC2626' }}
                      title="Remove workspace"
                      disabled={ws.status === 'IN_USE'}
                      onClick={(e) => handleQuickDelete(ws, e)}
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* Modals */}
      <CreateWorkspaceModal
        isOpen={isCreateModalOpen}
        project={currentProject}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={handleCreateWorkspace}
      />

      <WorkspaceDetailModal
        isOpen={isDetailModalOpen}
        workspace={selectedWorkspace}
        onClose={() => {
          setIsDetailModalOpen(false);
          setSelectedWorkspace(null);
        }}
        onWorkspaceDeleted={handleWorkspaceDeleted}
      />
    </div>
  );
};
