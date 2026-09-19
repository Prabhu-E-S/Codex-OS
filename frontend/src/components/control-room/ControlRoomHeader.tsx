import React from 'react';
import {
  PlayCircle,
  CheckCircle2,
  AlertCircle,
  PauseCircle,
  XCircle,
  RefreshCw,
  Clock,
  Layers,
  Bot,
  Radio,
} from 'lucide-react';
import { ControlRoomRun, ControlRoomOrchestration } from '../../api/types';

interface ControlRoomHeaderProps {
  run: ControlRoomRun;
  orchestration?: ControlRoomOrchestration | null;
  isPolling: boolean;
  isStale: boolean;
  lastUpdated: Date | null;
  onRefresh: () => void;
  refreshing: boolean;
}

export const ControlRoomHeader: React.FC<ControlRoomHeaderProps> = ({
  run,
  orchestration,
  isPolling,
  isStale,
  lastUpdated,
  onRefresh,
  refreshing,
}) => {
  // Format elapsed or total duration
  const formatDuration = (seconds?: number | null) => {
    if (seconds === undefined || seconds === null) return '—';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    if (m === 0) return `${s}s`;
    return `${m}m ${s}s`;
  };

  const getStatusBadge = () => {
    const status = run.status;
    const orchState = orchestration?.state;

    if (orchState === 'PAUSED' || status === 'PAUSED') {
      return (
        <span className="cr-status-badge cr-status-paused">
          <PauseCircle size={13} /> PAUSED
        </span>
      );
    }
    if (status === 'RUNNING' || status === 'STARTING') {
      return (
        <span className="cr-status-badge cr-status-running">
          <PlayCircle size={13} /> RUNNING
        </span>
      );
    }
    if (status === 'COMPLETED' || orchState === 'COMPLETED') {
      return (
        <span className="cr-status-badge cr-status-completed">
          <CheckCircle2 size={13} /> COMPLETED
        </span>
      );
    }
    if (status === 'FAILED' || orchState === 'FAILED') {
      return (
        <span className="cr-status-badge cr-status-failed">
          <AlertCircle size={13} /> FAILED
        </span>
      );
    }
    if (status === 'CANCELLED' || orchState === 'CANCELLED') {
      return (
        <span className="cr-status-badge cr-status-cancelled">
          <XCircle size={13} /> CANCELLED
        </span>
      );
    }
    return <span className="cr-status-badge cr-status-pending">{status}</span>;
  };

  return (
    <header className="cr-header">
      <div className="cr-header-top">
        <div className="cr-title-area">
          <div className="cr-project-tag">{run.project_name}</div>
          <h1 className="cr-run-title">
            Run #{run.id}
            <span className="cr-mode-pill">{run.mode}</span>
            {getStatusBadge()}
          </h1>
          <p className="cr-goal-desc">{run.goal}</p>
        </div>

        <div className="cr-header-actions">
          {/* Polling indicator */}
          <div className={`cr-live-pulse ${isPolling ? 'active' : 'idle'}`} title={isPolling ? 'Live updates active (polling every 3s)' : 'Updates idle'}>
            <Radio size={14} className={isPolling ? 'pulse-icon' : ''} />
            <span>{isPolling ? 'LIVE' : 'IDLE'}</span>
          </div>

          <button
            className="btn btn-secondary btn-sm"
            onClick={onRefresh}
            disabled={refreshing}
            title="Refresh snapshot now"
          >
            <RefreshCw size={13} className={refreshing ? 'spin-icon' : ''} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Stale warning banner if network had a temporary hiccup */}
      {isStale && (
        <div className="cr-stale-banner">
          <AlertCircle size={14} />
          <span>
            Connection temporarily unavailable. Displaying cached snapshot from{' '}
            {lastUpdated?.toLocaleTimeString() ?? 'recent'}.
          </span>
        </div>
      )}

      {/* Quick metadata strip */}
      <div className="cr-meta-strip">
        <div className="cr-meta-item">
          <Layers size={13} />
          <span>
            Iteration <strong>{run.iteration}</strong> of {run.max_iterations}
          </span>
        </div>

        {orchestration?.current_agent && (
          <div className="cr-meta-item">
            <Bot size={13} />
            <span>
              Active Agent: <strong>{orchestration.current_agent}</strong>
            </span>
          </div>
        )}

        <div className="cr-meta-item">
          <Clock size={13} />
          <span>
            Duration: <strong>{formatDuration(run.duration_seconds)}</strong>
          </span>
        </div>

        {lastUpdated && (
          <div className="cr-meta-item cr-last-updated">
            <span>Last updated: {lastUpdated.toLocaleTimeString()}</span>
          </div>
        )}
      </div>
    </header>
  );
};
