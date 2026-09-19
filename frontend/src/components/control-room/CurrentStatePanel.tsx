import React from 'react';
import { ControlRoomRun, ControlRoomOrchestration } from '../../api/types';
import { ArrowRight, Activity, ShieldCheck, RefreshCw } from 'lucide-react';

interface CurrentStatePanelProps {
  run: ControlRoomRun;
  orchestration?: ControlRoomOrchestration | null;
}

export const CurrentStatePanel: React.FC<CurrentStatePanelProps> = ({ run, orchestration }) => {
  const state = orchestration?.state || run.status;
  const currentAgent = orchestration?.current_agent || (run.status === 'RUNNING' ? 'Direct Codex Execution' : 'None');
  const iteration = run.iteration;
  const maxIterations = run.max_iterations;
  const lastDecision = orchestration?.last_decision;
  const lastDecisionReason = orchestration?.last_decision_reason;

  // Determine next step if deterministically known
  const getNextStep = () => {
    switch (state) {
      case 'PENDING':
        return 'Architect Agent';
      case 'ARCHITECTING':
        return 'Builder Agent';
      case 'BUILDING':
        return 'Tester Agent';
      case 'TESTING':
        return 'Breaker Agent';
      case 'BREAKING':
        return 'Security Agent';
      case 'SECURITY_SCANNING':
        return 'Orchestrator Decision';
      case 'DECIDING':
        return lastDecision === 'RETRY_BUILDER' ? 'Builder Agent (Iteration Retry)' : 'Completion & Evaluation';
      case 'ITERATING':
        return 'Builder Agent (Remediation)';
      case 'PAUSED':
        return 'Resume paused agent execution';
      case 'COMPLETED':
        return 'Evaluation & Engineering Score';
      default:
        return null;
    }
  };

  const nextStep = getNextStep();

  return (
    <div className="cr-current-state-panel">
      <div className="cr-state-header">
        <div className="cr-state-label">
          <Activity size={14} className="cr-state-icon" />
          <span>CURRENT STATE</span>
        </div>
        <div className="cr-state-badge-main">{state}</div>
      </div>

      <div className="cr-state-grid">
        <div className="cr-state-cell">
          <span className="cr-cell-label">Current Agent</span>
          <span className="cr-cell-value cr-highlight-agent">
            {currentAgent}
          </span>
        </div>

        <div className="cr-state-cell">
          <span className="cr-cell-label">Iteration Progress</span>
          <span className="cr-cell-value">
            Iteration <strong>{iteration}</strong> / {maxIterations}
          </span>
        </div>

        {lastDecision && (
          <div className="cr-state-cell cr-cell-wide">
            <div className="cr-decision-row">
              <span className="cr-cell-label">Last Decision</span>
              <span className={`cr-decision-tag tag-${lastDecision.toLowerCase()}`}>
                {lastDecision === 'RETRY_BUILDER' && <RefreshCw size={11} />}
                {lastDecision === 'STOP_SUCCESS' && <ShieldCheck size={11} />}
                {lastDecision}
              </span>
            </div>
            {lastDecisionReason && (
              <p className="cr-decision-reason-text">
                &ldquo;{lastDecisionReason}&rdquo;
              </p>
            )}
          </div>
        )}

        {nextStep && state !== 'COMPLETED' && state !== 'FAILED' && state !== 'CANCELLED' && (
          <div className="cr-state-cell cr-cell-next">
            <span className="cr-cell-label">Next Action</span>
            <div className="cr-next-row">
              <ArrowRight size={13} />
              <span>{nextStep}</span>
            </div>
          </div>
        )}

        {run.error_message && (
          <div className="cr-state-cell cr-cell-error cr-cell-wide">
            <span className="cr-cell-label">Error Notice</span>
            <p className="cr-error-text">{run.error_message}</p>
          </div>
        )}
      </div>
    </div>
  );
};
