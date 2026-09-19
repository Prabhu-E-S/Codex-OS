import React, { useState, useEffect, useRef } from 'react';
import {
  X,
  PlayCircle,
  StopCircle,
  Clock,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  Terminal,
  AlertTriangle,
  FolderGit2,
} from 'lucide-react';
import { EngineeringRun, RunLogsResponse } from '../api/types';
import { api } from '../api/client';

interface RunDetailModalProps {
  run: EngineeringRun | null;
  isOpen: boolean;
  onClose: () => void;
  onRunUpdated: (updatedRun: EngineeringRun) => void;
}

export const RunDetailModal: React.FC<RunDetailModalProps> = ({
  run,
  isOpen,
  onClose,
  onRunUpdated,
}) => {
  const [logs, setLogs] = useState<RunLogsResponse | null>(null);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll when logs change during active execution
  useEffect(() => {
    if (run && (run.status === 'RUNNING' || run.status === 'STARTING')) {
      terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, run]);

  // Fetch latest logs and run state
  const fetchLogsAndStatus = async (runId: number) => {
    try {
      const [logsData, updatedRun] = await Promise.all([
        api.getRunLogs(runId),
        api.getRun(runId),
      ]);
      setLogs(logsData);
      onRunUpdated(updatedRun);
    } catch (err) {
      console.error('Failed to fetch run logs:', err);
    }
  };

  // Initial load when modal opens
  useEffect(() => {
    if (isOpen && run) {
      setLoadingLogs(true);
      fetchLogsAndStatus(run.id).finally(() => setLoadingLogs(false));
    } else {
      setLogs(null);
    }
  }, [isOpen, run?.id]);

  // Polling while run is active (STARTING or RUNNING)
  useEffect(() => {
    if (!isOpen || !run) return;

    const isActive = run.status === 'STARTING' || run.status === 'RUNNING';
    if (!isActive) return;

    const intervalId = setInterval(() => {
      fetchLogsAndStatus(run.id);
    }, 1500);

    return () => clearInterval(intervalId);
  }, [isOpen, run?.status, run?.id]);

  if (!isOpen || !run) return null;

  const handleStartRun = async () => {
    setExecuting(true);
    try {
      const startedRun = await api.executeRun(run.id);
      onRunUpdated(startedRun);
      await fetchLogsAndStatus(run.id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to start execution');
    } finally {
      setExecuting(false);
    }
  };

  const handleCancelRun = async () => {
    if (!window.confirm('Are you sure you want to cancel this engineering run?')) return;
    setCancelling(true);
    try {
      const cancelledRun = await api.cancelRun(run.id);
      onRunUpdated(cancelledRun);
      await fetchLogsAndStatus(run.id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to cancel execution');
    } finally {
      setCancelling(false);
    }
  };

  const isActive = run.status === 'STARTING' || run.status === 'RUNNING';

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="badge badge-success">
            <CheckCircle2 size={11} /> COMPLETED
          </span>
        );
      case 'RUNNING':
        return (
          <span className="badge badge-accent">
            <span className="pulse-dot"></span> RUNNING
          </span>
        );
      case 'STARTING':
        return (
          <span className="badge badge-warning">
            <RefreshCw size={11} className="spinning" /> STARTING
          </span>
        );
      case 'TIMEOUT':
        return (
          <span className="badge badge-error">
            <Clock size={11} /> TIMEOUT
          </span>
        );
      case 'CANCELLED':
        return (
          <span className="badge badge-muted">
            <AlertTriangle size={11} /> CANCELLED
          </span>
        );
      case 'FAILED':
        return (
          <span className="badge badge-error">
            <AlertCircle size={11} /> FAILED
          </span>
        );
      default:
        return <span className="badge badge-neutral">PENDING</span>;
    }
  };

  const stdoutText = logs?.stdout ?? run.stdout ?? '';
  const stderrText = logs?.stderr ?? run.stderr ?? '';
  const errorMessage = logs?.error_message ?? run.error_message;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-dialog"
        style={{ maxWidth: '780px', width: '92%' }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <span style={{ fontFamily: 'var(--font-mono)', fontWeight: 600, fontSize: '13px' }}>
              Run #{run.id}
            </span>
            {getStatusBadge(run.status)}
          </div>
          <button
            className="btn btn-secondary btn-icon-only"
            onClick={onClose}
            aria-label="Close modal"
          >
            <X size={15} />
          </button>
        </div>

        <div className="modal-body" style={{ maxHeight: '78vh', overflowY: 'auto' }}>
          {/* Engineering Goal */}
          <div className="form-group">
            <label className="form-label" style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              Engineering Goal
            </label>
            <div
              style={{
                fontSize: '13.5px',
                fontWeight: 500,
                lineHeight: 1.5,
                color: 'var(--text-primary)',
                backgroundColor: 'var(--bg-hover)',
                padding: '10px 12px',
                borderRadius: '4px',
                border: '1px solid var(--border-light)',
              }}
            >
              {run.goal}
            </div>
          </div>

          {/* Isolated Workspace Banner */}
          {run.workspace_name && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '8px 12px',
                backgroundColor: '#ECFDF5',
                border: '1px solid #A7F3D0',
                borderRadius: '6px',
                fontSize: '12px',
                color: '#065F46',
                marginBottom: '14px',
              }}
            >
              <FolderGit2 size={15} color="#059669" style={{ flexShrink: 0 }} />
              <span>Isolated Worktree Workspace:</span>
              <strong style={{ fontFamily: 'JetBrains Mono, monospace', color: '#047857' }}>
                {run.workspace_name}
              </strong>
              <span style={{ color: '#10B981', marginLeft: 'auto', fontSize: '11px' }}>
                Executed in isolated branch &amp; directory
              </span>
            </div>
          )}

          {/* Telemetry metadata */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '12px',
              fontSize: '11.5px',
              color: 'var(--text-secondary)',
              borderBottom: '1px solid var(--border-light)',
              paddingBottom: '10px',
            }}
          >
            <div>
              <span style={{ color: 'var(--text-muted)' }}>Created: </span>
              {new Date(run.created_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </div>
            {run.started_at && (
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Started: </span>
                {new Date(run.started_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </div>
            )}
            {run.completed_at && (
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Completed: </span>
                {new Date(run.completed_at).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
              </div>
            )}
            {run.exit_code !== null && run.exit_code !== undefined && (
              <div>
                <span style={{ color: 'var(--text-muted)' }}>Exit Code: </span>
                <span className="mono-path" style={{ padding: '1px 5px', fontSize: '11px' }}>
                  {run.exit_code}
                </span>
              </div>
            )}
          </div>

          {/* Error Banner */}
          {errorMessage && (
            <div className="alert-banner alert-banner-error" style={{ marginBottom: 0 }}>
              <AlertCircle size={16} style={{ flexShrink: 0 }} />
              <div>
                <strong>Execution Notice: </strong>
                {errorMessage}
              </div>
            </div>
          )}

          {/* Terminal / Logs Output */}
          <div className="form-group">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
              <label className="form-label" style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Terminal size={14} color="#2563EB" />
                <span>Codex Execution Logs</span>
              </label>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {isActive && (
                  <span style={{ fontSize: '11px', color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <span className="pulse-dot"></span> Live streaming
                  </span>
                )}
                <button
                  className="btn btn-secondary btn-icon-only"
                  style={{ padding: '3px 6px', height: '24px' }}
                  onClick={() => fetchLogsAndStatus(run.id)}
                  title="Refresh logs"
                  disabled={loadingLogs}
                >
                  <RefreshCw size={11} className={loadingLogs ? 'spinning' : ''} />
                </button>
              </div>
            </div>

            <div className="terminal-panel">
              {stdoutText || stderrText ? (
                <>
                  {stdoutText && (
                    <div className="terminal-stdout">
                      {stdoutText}
                    </div>
                  )}
                  {stderrText && (
                    <div className="terminal-stderr">
                      {stderrText}
                    </div>
                  )}
                  <div ref={terminalEndRef} />
                </>
              ) : (
                <div className="terminal-empty">
                  {isActive
                    ? 'Codex is starting execution... Live logs will stream here.'
                    : 'No output captured for this run yet.'}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
          <div>
            {isActive ? (
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={handleCancelRun}
                disabled={cancelling}
                id="btn-cancel-run-modal"
              >
                <StopCircle size={13} />
                <span>{cancelling ? 'Cancelling...' : 'Cancel Run'}</span>
              </button>
            ) : (
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={handleStartRun}
                disabled={executing}
                id="btn-execute-run-modal"
              >
                <PlayCircle size={13} />
                <span>{executing ? 'Starting...' : 'Start Engineering Run'}</span>
              </button>
            )}
          </div>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={onClose}
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
