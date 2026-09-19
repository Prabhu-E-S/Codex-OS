import React from 'react';
import {
  PlayCircle,
  Plus,
  Clock,
  FileCode2,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  AlertTriangle,
  Play,
  Terminal,
  FolderGit2,
  Activity,
} from 'lucide-react';
import { EngineeringRun, Project } from '../api/types';

interface RunsTableProps {
  runs: EngineeringRun[];
  project: Project | null;
  loading: boolean;
  onOpenCreateRun: () => void;
  onSelectRun: (run: EngineeringRun) => void;
  onExecuteRun: (runId: number) => Promise<void>;
  onOpenControlRoom?: (runId: number) => void;
}

export const RunsTable: React.FC<RunsTableProps> = ({
  runs,
  project,
  loading,
  onOpenCreateRun,
  onSelectRun,
  onExecuteRun,
  onOpenControlRoom,
}) => {
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

  return (
    <div className="card-panel">
      <div className="card-header">
        <div className="card-title">
          <PlayCircle size={15} color="#2563EB" />
          <span>Engineering Runs</span>
          <span className="badge badge-neutral" style={{ marginLeft: '4px' }}>
            {runs.length}
          </span>
        </div>
        {project && (
          <button
            className="btn btn-secondary btn-sm"
            onClick={onOpenCreateRun}
            id="btn-create-run"
          >
            <Plus size={13} />
            <span>New Run</span>
          </button>
        )}
      </div>

      {loading ? (
        <div className="empty-state" style={{ padding: '24px' }}>
          <div className="empty-desc">Loading engineering runs...</div>
        </div>
      ) : runs.length === 0 ? (
        <div className="empty-state">
          <div className="empty-icon">
            <Clock size={20} />
          </div>
          <div className="empty-title">No engineering runs yet.</div>
          <div className="empty-desc">
            {project
              ? 'Start your first engineering run record for this project.'
              : 'Create a project and start your first engineering run.'}
          </div>
          {project && (
            <button
              className="btn btn-primary btn-sm"
              onClick={onOpenCreateRun}
              style={{ marginTop: '6px' }}
            >
              Start Engineering Run
            </button>
          )}
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '60px' }}>ID</th>
                <th style={{ width: '125px' }}>Status</th>
                <th>Engineering Goal</th>
                <th style={{ width: '140px' }}>Created</th>
                <th style={{ width: '130px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => {
                const createdStr = new Date(run.created_at).toLocaleDateString('en-US', {
                  month: 'short',
                  day: 'numeric',
                  hour: '2-digit',
                  minute: '2-digit',
                });

                const isPending = run.status === 'PENDING';

                return (
                  <tr
                    key={run.id}
                    className="table-row-clickable"
                    onClick={() => onSelectRun(run)}
                  >
                    <td>
                      <span className="mono-path" style={{ fontSize: '11px' }}>
                        #{run.id}
                      </span>
                    </td>
                    <td>{getStatusBadge(run.status)}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '6px' }}>
                        <FileCode2 size={14} color="#6B6B67" style={{ marginTop: '2px', flexShrink: 0 }} />
                        <div>
                          <div style={{ fontWeight: 500 }}>{run.goal}</div>
                          {run.workspace_name && (
                            <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginTop: '3px' }}>
                              <span
                                style={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: '4px',
                                  fontSize: '10.5px',
                                  backgroundColor: '#ECFDF5',
                                  color: '#059669',
                                  border: '1px solid #A7F3D0',
                                  padding: '1px 6px',
                                  borderRadius: '4px',
                                  fontFamily: 'JetBrains Mono, monospace',
                                }}
                              >
                                <FolderGit2 size={10} />
                                <span>{run.workspace_name}</span>
                              </span>
                            </div>
                          )}
                        </div>
                      </div>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '11.5px' }}>
                      {createdStr}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}>
                        {isPending && (
                          <button
                            className="btn btn-primary btn-sm"
                            style={{ padding: '3px 8px', fontSize: '11px' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              onExecuteRun(run.id);
                            }}
                            title="Execute this run"
                          >
                            <Play size={10} />
                            <span>Run</span>
                          </button>
                        )}
                        {onOpenControlRoom && (
                          <button
                            className="btn btn-secondary btn-sm"
                            style={{ padding: '3px 7px', fontSize: '11px' }}
                            onClick={(e) => {
                              e.stopPropagation();
                              onOpenControlRoom(run.id);
                            }}
                            title="Open in Control Room"
                          >
                            <Activity size={11} color="#2563EB" />
                            <span>Control Room</span>
                          </button>
                        )}
                        <button
                          className="btn btn-secondary btn-sm"
                          style={{ padding: '3px 7px', fontSize: '11px' }}
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectRun(run);
                          }}
                          title="Open terminal logs"
                        >
                          <Terminal size={11} />
                          <span>Logs</span>
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div
        style={{
          padding: '8px 16px',
          borderTop: '1px solid var(--border-light)',
          backgroundColor: 'var(--bg-hover)',
          fontSize: '11px',
          color: 'var(--text-muted)',
        }}
      >
        Note: Click any run row to view live Codex terminal output, execution timestamps, and cancellation controls.
      </div>
    </div>
  );
};
