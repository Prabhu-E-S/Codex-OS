import React from 'react';
import { Activity, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { HealthResponse } from '../api/types';

interface SystemStatusCardProps {
  health: HealthResponse | null;
  loading: boolean;
  onRefresh: () => void;
}

export const SystemStatusCard: React.FC<SystemStatusCardProps> = ({
  health,
  loading,
  onRefresh,
}) => {
  const isBackendConnected = Boolean(health);
  const isDatabaseConnected = health?.database === 'connected';

  return (
    <div className="card-panel">
      <div className="card-header">
        <div className="card-title">
          <Activity size={15} color="#2563EB" />
          <span>System Status</span>
        </div>
        <button
          className="btn btn-secondary btn-icon-only"
          onClick={onRefresh}
          disabled={loading}
          title="Refresh connection status"
          aria-label="Refresh status"
        >
          <RefreshCw size={13} className={loading ? 'spinning' : ''} />
        </button>
      </div>

      <div className="card-body">
        <div className="status-matrix">
          {/* Backend */}
          <div className="status-row">
            <div className="status-label">
              <span>Backend</span>
            </div>
            {isBackendConnected ? (
              <span className="badge badge-success">
                <CheckCircle2 size={11} /> Connected
              </span>
            ) : (
              <span className="badge badge-error">
                <AlertCircle size={11} /> Disconnected
              </span>
            )}
          </div>

          {/* Database */}
          <div className="status-row">
            <div className="status-label">
              <span>Database</span>
            </div>
            {isDatabaseConnected ? (
              <span className="badge badge-success" title={health?.database_dialect ? `Dialect: ${health.database_dialect}` : undefined}>
                <CheckCircle2 size={11} /> Connected {health?.database_dialect ? `(${health.database_dialect})` : ''}
              </span>
            ) : (
              <span className="badge badge-error" title={health?.database_error || 'Database unreachable'}>
                <AlertCircle size={11} /> {isBackendConnected ? 'Disconnected' : 'Unavailable'}
              </span>
            )}
          </div>

          {/* Agent Engine */}
          <div className="status-row">
            <div className="status-label">
              <span>Agent Engine</span>
            </div>
            <span className="badge badge-muted">
              Not configured <span className="phase-tag" style={{ marginLeft: '4px' }}>Phase 2</span>
            </span>
          </div>

          {/* Sandbox */}
          <div className="status-row">
            <div className="status-label">
              <span>Sandbox</span>
            </div>
            <span className="badge badge-muted">
              Not configured <span className="phase-tag" style={{ marginLeft: '4px' }}>Phase 2</span>
            </span>
          </div>

          {/* Evaluator */}
          <div className="status-row">
            <div className="status-label">
              <span>Evaluator</span>
            </div>
            <span className="badge badge-muted">
              Not configured <span className="phase-tag" style={{ marginLeft: '4px' }}>Phase 2</span>
            </span>
          </div>
        </div>

        <div style={{ marginTop: '14px', fontSize: '11.5px', color: 'var(--text-muted)' }}>
          Codex OS core foundation active. Autonomous execution subsystems are scheduled for Phase 2.
        </div>
      </div>
    </div>
  );
};
