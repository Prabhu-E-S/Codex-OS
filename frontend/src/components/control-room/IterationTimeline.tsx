import React from 'react';
import {
  Layers,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
  RefreshCw,
  ShieldCheck,
  Clock,
  AlertTriangle,
} from 'lucide-react';
import { ControlRoomIteration } from '../../api/types';

interface IterationTimelineProps {
  iterations: ControlRoomIteration[];
  currentIteration: number;
}

export const IterationTimeline: React.FC<IterationTimelineProps> = ({
  iterations,
  currentIteration,
}) => {
  const formatDuration = (sec?: number | null) => {
    if (sec === undefined || sec === null) return '—';
    if (sec < 1) return '<1s';
    return `${Math.round(sec)}s`;
  };

  if (!iterations || iterations.length === 0) {
    return (
      <div className="cr-empty-card">
        <Layers size={20} className="text-muted" />
        <span>No iteration data available yet.</span>
      </div>
    );
  }

  return (
    <div className="cr-iterations-card">
      <div className="cr-card-header">
        <h3 className="cr-card-title">Iteration History & Decisions</h3>
        <span className="cr-card-subtitle">
          Recorded remediation cycles and deterministic decision policy justifications
        </span>
      </div>

      <div className="cr-iterations-list">
        {iterations.map((iter) => {
          const isCurrent = iter.iteration_number === currentIteration;

          return (
            <div
              key={iter.iteration_number}
              className={`cr-iteration-card ${isCurrent ? 'is-current-iter' : ''}`}
            >
              <div className="cr-iter-card-top">
                <div className="cr-iter-title">
                  <Layers size={14} />
                  <span>Iteration {iter.iteration_number}</span>
                  {isCurrent && <span className="cr-iter-current-tag">Active Iteration</span>}
                </div>

                <div className="cr-iter-status-tag">
                  {iter.status === 'COMPLETED' && <CheckCircle2 size={12} className="text-success" />}
                  {iter.status === 'RUNNING' && <PlayCircle size={12} className="text-blue" />}
                  {iter.status === 'RETRYING' && <RefreshCw size={12} className="text-amber" />}
                  {iter.status === 'FAILED' && <AlertCircle size={12} className="text-error" />}
                  <span>{iter.status}</span>
                </div>
              </div>

              {/* Agent mini-list in this iteration */}
              <div className="cr-iter-agents-row">
                {iter.agents.length > 0 ? (
                  iter.agents.map((ag, idx) => (
                    <div key={idx} className={`cr-iter-agent-pill agent-${ag.status.toLowerCase()}`}>
                      <span className="agent-pill-name">{ag.agent_name}</span>
                      <span className="agent-pill-dur">
                        <Clock size={10} /> {formatDuration(ag.duration_seconds)}
                      </span>
                      {ag.findings_count > 0 && (
                        <span className="agent-pill-findings">
                          <AlertTriangle size={10} /> {ag.findings_count}
                        </span>
                      )}
                    </div>
                  ))
                ) : (
                  <span className="cr-iter-no-agents text-muted">No agent steps recorded yet</span>
                )}
              </div>

              {/* Decision and transparent reason */}
              {iter.decision ? (
                <div className="cr-iter-decision-box">
                  <div className="decision-header">
                    <span className="decision-label">Policy Decision:</span>
                    <span className={`cr-decision-tag tag-${iter.decision.toLowerCase()}`}>
                      {iter.decision === 'RETRY_BUILDER' && <RefreshCw size={11} />}
                      {iter.decision === 'STOP_SUCCESS' && <ShieldCheck size={11} />}
                      {iter.decision}
                    </span>
                  </div>
                  {iter.decision_reason && (
                    <p className="decision-reason-text">&ldquo;{iter.decision_reason}&rdquo;</p>
                  )}
                </div>
              ) : isCurrent ? (
                <div className="cr-iter-pending-decision text-muted">
                  Iteration in progress. Deterministic decision pending tester, breaker, and security scans.
                </div>
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
};
