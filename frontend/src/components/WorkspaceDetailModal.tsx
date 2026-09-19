import React, { useState, useEffect } from 'react';
import {
  X,
  GitBranch,
  FolderGit2,
  Trash2,
  Check,
  Copy,
  AlertCircle,
  HardDrive,
  Box,
  Play,
  Square,
  Terminal,
  RefreshCw,
  Plus,
} from 'lucide-react';
import { Workspace, Sandbox, CommandResult, DockerStatusResponse } from '../api/types';
import { api } from '../api/client';

interface WorkspaceDetailModalProps {
  workspace: Workspace | null;
  isOpen: boolean;
  onClose: () => void;
  onWorkspaceDeleted: (workspaceId: number) => void;
}

export const WorkspaceDetailModal: React.FC<WorkspaceDetailModalProps> = ({
  workspace,
  isOpen,
  onClose,
  onWorkspaceDeleted,
}) => {
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  // Sandbox state
  const [sandbox, setSandbox] = useState<Sandbox | null>(null);
  const [loadingSandbox, setLoadingSandbox] = useState(false);
  const [dockerStatus, setDockerStatus] = useState<DockerStatusResponse | null>(null);
  const [sandboxActionLoading, setSandboxActionLoading] = useState(false);
  const [sandboxError, setSandboxError] = useState<string | null>(null);

  // Command execution state
  const [commandInput, setCommandInput] = useState('python --version');
  const [executingCommand, setExecutingCommand] = useState(false);
  const [commandResult, setCommandResult] = useState<CommandResult | null>(null);

  const fetchSandboxAndDocker = async (wsId: number) => {
    setLoadingSandbox(true);
    setSandboxError(null);
    try {
      const [sb, ds] = await Promise.all([
        api.getWorkspaceSandbox(wsId),
        api.getDockerStatus().catch(() => null),
      ]);
      setSandbox(sb);
      setDockerStatus(ds);
    } catch (err: unknown) {
      console.error('Failed to load sandbox:', err);
    } finally {
      setLoadingSandbox(false);
    }
  };

  useEffect(() => {
    if (isOpen && workspace) {
      fetchSandboxAndDocker(workspace.id);
      setCommandResult(null);
    } else {
      setSandbox(null);
      setDockerStatus(null);
      setCommandResult(null);
    }
  }, [isOpen, workspace?.id]);

  if (!isOpen || !workspace) return null;

  const copyToClipboard = (text: string, fieldName: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldName);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to remove worktree workspace "${workspace.name}"? This will prune the Git worktree and delete the workspace directory.`)) {
      return;
    }

    setDeleting(true);
    setDeleteError(null);
    try {
      await api.deleteWorkspace(workspace.id);
      onWorkspaceDeleted(workspace.id);
      onClose();
    } catch (err: unknown) {
      if (err instanceof Error) {
        setDeleteError(err.message);
      } else {
        setDeleteError('Failed to delete workspace');
      }
    } finally {
      setDeleting(false);
    }
  };

  // Sandbox lifecycle handlers
  const handleCreateSandbox = async () => {
    setSandboxActionLoading(true);
    setSandboxError(null);
    try {
      const newSb = await api.createSandbox(workspace.id);
      setSandbox(newSb);
    } catch (err: unknown) {
      setSandboxError(err instanceof Error ? err.message : 'Failed to create sandbox');
    } finally {
      setSandboxActionLoading(false);
    }
  };

  const handleStartSandbox = async () => {
    if (!sandbox) return;
    setSandboxActionLoading(true);
    setSandboxError(null);
    try {
      const started = await api.startSandbox(sandbox.id);
      setSandbox(started);
    } catch (err: unknown) {
      setSandboxError(err instanceof Error ? err.message : 'Failed to start sandbox');
    } finally {
      setSandboxActionLoading(false);
    }
  };

  const handleStopSandbox = async () => {
    if (!sandbox) return;
    setSandboxActionLoading(true);
    setSandboxError(null);
    try {
      const stopped = await api.stopSandbox(sandbox.id);
      setSandbox(stopped);
    } catch (err: unknown) {
      setSandboxError(err instanceof Error ? err.message : 'Failed to stop sandbox');
    } finally {
      setSandboxActionLoading(false);
    }
  };

  const handleRemoveSandbox = async () => {
    if (!sandbox) return;
    if (!window.confirm('Are you sure you want to remove this sandbox container? Workspace files will remain intact.')) return;
    setSandboxActionLoading(true);
    setSandboxError(null);
    try {
      const removed = await api.deleteSandbox(sandbox.id);
      setSandbox(removed);
      setCommandResult(null);
    } catch (err: unknown) {
      setSandboxError(err instanceof Error ? err.message : 'Failed to remove sandbox');
    } finally {
      setSandboxActionLoading(false);
    }
  };

  const handleExecuteCommand = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!sandbox || !commandInput.trim()) return;

    setExecutingCommand(true);
    try {
      const res = await api.executeSandboxCommand(sandbox.id, {
        command: commandInput.trim(),
        timeout: 30,
      });
      setCommandResult(res);
      // Refresh sandbox state if needed
      const updated = await api.getSandbox(sandbox.id);
      setSandbox(updated);
    } catch (err: unknown) {
      setCommandResult({
        exit_code: -1,
        stdout: '',
        stderr: err instanceof Error ? err.message : 'Execution failed',
        duration_ms: 0,
        timed_out: false,
        error_message: err instanceof Error ? err.message : 'Execution failed',
      });
    } finally {
      setExecutingCommand(false);
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

  const getSandboxBadge = (status?: string) => {
    switch (status) {
      case 'RUNNING':
        return { label: 'Running', bg: '#ECFDF5', color: '#059669', border: '#A7F3D0' };
      case 'CREATED':
        return { label: 'Created', bg: '#EFF6FF', color: '#2563EB', border: '#BFDBFE' };
      case 'STARTING':
      case 'STOPPING':
        return { label: status, bg: '#FFFBEB', color: '#D97706', border: '#FDE68A' };
      case 'STOPPED':
        return { label: 'Stopped', bg: '#F1F5F9', color: '#475569', border: '#CBD5E1' };
      case 'FAILED':
        return { label: 'Failed', bg: '#FEF2F2', color: '#DC2626', border: '#FECACA' };
      case 'REMOVED':
      default:
        return { label: 'No Sandbox', bg: '#F8FAFC', color: '#94A3B8', border: '#E2E8F0' };
    }
  };

  const badge = getStatusBadge(workspace.status);
  const sbBadge = getSandboxBadge(sandbox?.status);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '680px', maxHeight: '90vh', overflowY: 'auto' }}>
        <div className="modal-header">
          <div className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FolderGit2 size={18} color="#059669" />
            <span>Workspace: {workspace.name}</span>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: '9999px',
                backgroundColor: badge.bg,
                color: badge.color,
                border: `1px solid ${badge.border}`,
                marginLeft: '6px',
              }}
            >
              {badge.label}
            </span>
          </div>
          <button
            className="btn btn-secondary btn-icon-only"
            onClick={onClose}
            aria-label="Close modal"
          >
            <X size={15} />
          </button>
        </div>

        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {deleteError && (
            <div className="alert-banner alert-banner-error">
              {deleteError}
            </div>
          )}

          {/* Docker Daemon Status Banner */}
          {dockerStatus && !dockerStatus.available && (
            <div
              style={{
                backgroundColor: '#FFFBEB',
                border: '1px solid #FDE68A',
                borderRadius: '6px',
                padding: '10px 12px',
                fontSize: '12px',
                color: '#92400E',
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
              }}
            >
              <AlertCircle size={15} color="#D97706" style={{ flexShrink: 0 }} />
              <div>
                <strong>Docker Notice: </strong>
                {dockerStatus.message}
              </div>
            </div>
          )}

          {/* Workspace Path & Git Branch details */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {/* Git Branch */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                backgroundColor: '#F8FAFC',
                border: '1px solid #E2E8F0',
                borderRadius: '6px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                <GitBranch size={15} color="#059669" style={{ flexShrink: 0 }} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 500 }}>Git Branch</div>
                  <div
                    style={{
                      fontSize: '12px',
                      fontFamily: 'JetBrains Mono, monospace',
                      color: '#0F172A',
                      fontWeight: 500,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {workspace.branch_name}
                  </div>
                </div>
              </div>
              <button
                className="btn btn-secondary btn-icon-only"
                style={{ padding: '4px', height: 'auto', marginLeft: '8px' }}
                onClick={() => copyToClipboard(workspace.branch_name, 'branch')}
                title="Copy branch name"
              >
                {copiedField === 'branch' ? <Check size={13} color="#059669" /> : <Copy size={13} />}
              </button>
            </div>

            {/* Worktree Directory */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '8px 12px',
                backgroundColor: '#F8FAFC',
                border: '1px solid #E2E8F0',
                borderRadius: '6px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0 }}>
                <HardDrive size={15} color="#3B82F6" style={{ flexShrink: 0 }} />
                <div style={{ minWidth: 0 }}>
                  <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 500 }}>Worktree Directory (Host Path)</div>
                  <div
                    style={{
                      fontSize: '12px',
                      fontFamily: 'JetBrains Mono, monospace',
                      color: '#0F172A',
                      fontWeight: 500,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {workspace.path}
                  </div>
                </div>
              </div>
              <button
                className="btn btn-secondary btn-icon-only"
                style={{ padding: '4px', height: 'auto', marginLeft: '8px' }}
                onClick={() => copyToClipboard(workspace.path, 'path')}
                title="Copy worktree path"
              >
                {copiedField === 'path' ? <Check size={13} color="#059669" /> : <Copy size={13} />}
              </button>
            </div>
          </div>

          {/* DOCKER SANDBOX SECTION */}
          <div
            style={{
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              padding: '14px',
              backgroundColor: '#FFFFFF',
              boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Box size={16} color="#2563EB" />
                <span style={{ fontWeight: 600, fontSize: '13px', color: '#0F172A' }}>Docker Sandbox Engine</span>
                {loadingSandbox ? (
                  <span style={{ fontSize: '11px', color: '#94A3B8', display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                    <RefreshCw size={11} className="spin-slow" /> Loading...
                  </span>
                ) : (
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '9999px',
                      backgroundColor: sbBadge.bg,
                      color: sbBadge.color,
                      border: `1px solid ${sbBadge.border}`,
                    }}
                  >
                    {sbBadge.label}
                  </span>
                )}
              </div>

              {/* Action buttons */}
              <div style={{ display: 'flex', gap: '6px' }}>
                {(!sandbox || sandbox.status === 'REMOVED') && (
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleCreateSandbox}
                    disabled={sandboxActionLoading}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', padding: '4px 8px' }}
                  >
                    <Plus size={12} />
                    <span>Create Sandbox</span>
                  </button>
                )}

                {sandbox && sandbox.status !== 'REMOVED' && (
                  <>
                    {(sandbox.status === 'CREATED' || sandbox.status === 'STOPPED') && (
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={handleStartSandbox}
                        disabled={sandboxActionLoading}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', padding: '4px 8px' }}
                      >
                        <Play size={11} />
                        <span>Start</span>
                      </button>
                    )}

                    {sandbox.status === 'RUNNING' && (
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={handleStopSandbox}
                        disabled={sandboxActionLoading}
                        style={{ display: 'inline-flex', alignItems: 'center', gap: '4px', fontSize: '11px', padding: '4px 8px' }}
                      >
                        <Square size={11} />
                        <span>Stop</span>
                      </button>
                    )}

                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={handleRemoveSandbox}
                      disabled={sandboxActionLoading}
                      style={{ color: '#DC2626', fontSize: '11px', padding: '4px 8px' }}
                      title="Destroy container (workspace files are preserved)"
                    >
                      <Trash2 size={11} />
                      <span>Remove</span>
                    </button>
                  </>
                )}
              </div>
            </div>

            {sandboxError && (
              <div className="alert-banner alert-banner-error" style={{ marginBottom: '10px', fontSize: '12px' }}>
                {sandboxError}
              </div>
            )}

            {/* Sandbox specifications */}
            {sandbox && sandbox.status !== 'REMOVED' ? (
              <div
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                  gap: '8px',
                  backgroundColor: '#F8FAFC',
                  padding: '10px',
                  borderRadius: '6px',
                  fontSize: '11px',
                }}
              >
                <div>
                  <span style={{ color: '#64748B' }}>Image:</span>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', color: '#0F172A', fontWeight: 500 }}>
                    {sandbox.image}
                  </div>
                </div>
                <div>
                  <span style={{ color: '#64748B' }}>CPU Limit:</span>
                  <div style={{ color: '#0F172A', fontWeight: 500 }}>{sandbox.cpu_limit} CPU</div>
                </div>
                <div>
                  <span style={{ color: '#64748B' }}>Memory Limit:</span>
                  <div style={{ color: '#0F172A', fontWeight: 500 }}>{sandbox.memory_limit}</div>
                </div>
                <div>
                  <span style={{ color: '#64748B' }}>Network:</span>
                  <div style={{ color: sandbox.network_enabled ? '#D97706' : '#059669', fontWeight: 500 }}>
                    {sandbox.network_enabled ? 'Bridge' : 'none (Isolated)'}
                  </div>
                </div>
                <div>
                  <span style={{ color: '#64748B' }}>Container ID:</span>
                  <div style={{ fontFamily: 'JetBrains Mono, monospace', color: '#0F172A' }}>
                    {sandbox.container_id ? sandbox.container_id.slice(0, 12) : 'None'}
                  </div>
                </div>
              </div>
            ) : (
              <div style={{ fontSize: '12px', color: '#64748B', lineHeight: 1.4 }}>
                Provision a disposable Docker container to execute commands and engineering runs inside an isolated <code style={{ backgroundColor: '#F1F5F9', padding: '1px 4px', borderRadius: '3px' }}>/workspace</code> directory with resource and network limits.
              </div>
            )}

            {/* SANDBOX TERMINAL / COMMAND TEST PANEL */}
            {sandbox && sandbox.status !== 'REMOVED' && (
              <div style={{ marginTop: '14px', borderTop: '1px solid #F1F5F9', paddingTop: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600, color: '#0F172A' }}>
                    <Terminal size={14} color="#2563EB" />
                    <span>Sandbox Terminal Test Panel</span>
                  </div>
                  <span style={{ fontSize: '10px', color: '#059669', backgroundColor: '#ECFDF5', border: '1px solid #A7F3D0', padding: '1px 6px', borderRadius: '4px' }}>
                    Mounted at /workspace
                  </span>
                </div>

                <form onSubmit={handleExecuteCommand} style={{ display: 'flex', gap: '8px' }}>
                  <input
                    type="text"
                    className="input-field"
                    style={{ flex: 1, fontFamily: 'JetBrains Mono, monospace', fontSize: '12px', padding: '6px 10px' }}
                    placeholder="Enter command inside container, e.g. python --version, ls -la"
                    value={commandInput}
                    onChange={(e) => setCommandInput(e.target.value)}
                    disabled={executingCommand}
                  />
                  <button
                    type="submit"
                    className="btn btn-primary btn-sm"
                    disabled={executingCommand || !commandInput.trim()}
                    style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}
                  >
                    {executingCommand ? <RefreshCw size={12} className="spin-animation" /> : <Play size={12} />}
                    <span>{executingCommand ? 'Executing...' : 'Run'}</span>
                  </button>
                </form>

                {/* Quick preset buttons */}
                <div style={{ display: 'flex', gap: '6px', marginTop: '6px' }}>
                  {['python --version', 'ls -la', 'python -c "print(1+1)"'].map((preset) => (
                    <button
                      key={preset}
                      type="button"
                      style={{
                        fontSize: '10px',
                        fontFamily: 'JetBrains Mono, monospace',
                        padding: '2px 6px',
                        backgroundColor: '#F8FAFC',
                        border: '1px solid #E2E8F0',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        color: '#475569',
                      }}
                      onClick={() => setCommandInput(preset)}
                    >
                      {preset}
                    </button>
                  ))}
                </div>

                {/* Command output display */}
                {commandResult && (
                  <div
                    style={{
                      marginTop: '10px',
                      backgroundColor: '#0F172A',
                      color: '#F8FAFC',
                      padding: '10px',
                      borderRadius: '6px',
                      fontFamily: 'JetBrains Mono, monospace',
                      fontSize: '11px',
                      maxHeight: '180px',
                      overflowY: 'auto',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94A3B8', borderBottom: '1px solid #334155', paddingBottom: '4px', marginBottom: '6px' }}>
                      <span>Exit Code: {commandResult.exit_code}</span>
                      <span>Duration: {commandResult.duration_ms}ms</span>
                    </div>

                    {commandResult.stdout && (
                      <pre style={{ margin: 0, color: '#A7F3D0', whiteSpace: 'pre-wrap' }}>
                        {commandResult.stdout}
                      </pre>
                    )}

                    {commandResult.stderr && (
                      <pre style={{ margin: 0, color: '#FECACA', whiteSpace: 'pre-wrap' }}>
                        {commandResult.stderr}
                      </pre>
                    )}

                    {!commandResult.stdout && !commandResult.stderr && (
                      <div style={{ color: '#64748B', fontStyle: 'italic' }}>[Process produced no output]</div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Meta Timestamps */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: '1fr 1fr',
              gap: '10px',
              fontSize: '11px',
              color: '#64748B',
            }}
          >
            <div>
              <span>Created: </span>
              <strong>{new Date(workspace.created_at).toLocaleString()}</strong>
            </div>
            <div>
              <span>Updated: </span>
              <strong>{new Date(workspace.updated_at).toLocaleString()}</strong>
            </div>
          </div>
        </div>

        <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
          <button
            type="button"
            className="btn btn-secondary"
            style={{ color: '#DC2626', borderColor: '#FECACA' }}
            onClick={handleDelete}
            disabled={deleting || workspace.status === 'IN_USE'}
            title={workspace.status === 'IN_USE' ? 'Cannot remove workspace while execution is running' : 'Remove worktree'}
          >
            <Trash2 size={13} style={{ marginRight: '6px' }} />
            <span>{deleting ? 'Removing Worktree...' : 'Remove Workspace'}</span>
          </button>

          <button type="button" className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
