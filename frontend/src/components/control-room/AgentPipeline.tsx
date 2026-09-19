import React from 'react';
import {
  Compass,
  Hammer,
  CheckCheck,
  Zap,
  Lock,
  Award,
  ArrowRight,
  Clock,
  AlertTriangle,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
} from 'lucide-react';
import { ControlRoomAgent, ControlRoomEvaluation } from '../../api/types';

interface AgentPipelineProps {
  agents: ControlRoomAgent[];
  activeAgentName?: string | null;
  currentIteration: number;
  evaluation?: ControlRoomEvaluation | null;
  onSelectAgent: (agent: ControlRoomAgent) => void;
  onSelectEvaluation?: () => void;
}

interface PipelineStep {
  type: string;
  name: string;
  icon: React.ReactNode;
  description: string;
}

const STEPS: PipelineStep[] = [
  { type: 'ARCHITECT', name: 'Architect', icon: <Compass size={15} />, description: 'Inspects codebase & creates implementation plan' },
  { type: 'BUILDER', name: 'Builder', icon: <Hammer size={15} />, description: 'Implements code in isolated worktree' },
  { type: 'TESTER', name: 'Tester', icon: <CheckCheck size={15} />, description: 'Runs tests in Docker sandbox' },
  { type: 'BREAKER', name: 'Breaker', icon: <Zap size={15} />, description: 'Adversarial edge-case & boundary testing' },
  { type: 'SECURITY', name: 'Security', icon: <Lock size={15} />, description: 'Automated vulnerability & secrets scanning' },
  { type: 'EVALUATION', name: 'Evaluation', icon: <Award size={15} />, description: 'Objective Engineering Score calculation' },
];

export const AgentPipeline: React.FC<AgentPipelineProps> = ({
  agents,
  activeAgentName,
  currentIteration: _currentIteration,
  evaluation,
  onSelectAgent,
  onSelectEvaluation,
}) => {
  // Find the latest execution for a given agent type
  const getLatestExecution = (type: string): ControlRoomAgent | undefined => {
    // Filter agents of this type, sort descending by iteration and id
    const matched = agents.filter((a) => a.agent_type.toUpperCase() === type.toUpperCase());
    if (matched.length === 0) return undefined;
    return matched[matched.length - 1];
  };

  const formatDuration = (sec?: number | null) => {
    if (sec === undefined || sec === null) return '—';
    if (sec < 1) return '<1s';
    return `${Math.round(sec)}s`;
  };

  return (
    <div className="cr-pipeline-card">
      <div className="cr-card-header">
        <h3 className="cr-card-title">Agent Pipeline</h3>
        <span className="cr-card-subtitle">
          Sequential execution flow across isolated environments
        </span>
      </div>

      <div className="cr-pipeline-track">
        {STEPS.map((step, idx) => {
          const isEvalStep = step.type === 'EVALUATION';
          const agentExec = !isEvalStep ? getLatestExecution(step.type) : undefined;
          const isActive =
            activeAgentName &&
            (activeAgentName.toUpperCase().includes(step.type) ||
              step.name.toUpperCase().includes(activeAgentName.toUpperCase()));

          // Determine step status
          let status: 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED' = 'PENDING';
          if (isEvalStep) {
            if (evaluation?.status === 'COMPLETED') status = 'COMPLETED';
            else if (evaluation?.status === 'EVALUATING') status = 'RUNNING';
            else if (evaluation?.status === 'FAILED') status = 'FAILED';
            else status = 'PENDING';
          } else if (agentExec) {
            status = agentExec.status as 'PENDING' | 'RUNNING' | 'COMPLETED' | 'FAILED';
          } else if (isActive) {
            status = 'RUNNING';
          }

          return (
            <React.Fragment key={step.type}>
              <div
                className={`cr-pipeline-step step-${status.toLowerCase()} ${isActive ? 'is-active' : ''}`}
                onClick={() => {
                  if (isEvalStep && onSelectEvaluation) {
                    onSelectEvaluation();
                  } else if (agentExec) {
                    onSelectAgent(agentExec);
                  }
                }}
                role="button"
                tabIndex={0}
                title={`Click to view details for ${step.name}`}
              >
                <div className="cr-step-top">
                  <div className="cr-step-icon">{step.icon}</div>
                  <div className={`cr-step-status-pill status-${status.toLowerCase()}`}>
                    {status === 'COMPLETED' && <CheckCircle2 size={10} />}
                    {status === 'RUNNING' && <PlayCircle size={10} />}
                    {status === 'FAILED' && <AlertCircle size={10} />}
                    <span>{status}</span>
                  </div>
                </div>

                <div className="cr-step-name">{step.name}</div>

                <div className="cr-step-meta">
                  {isEvalStep ? (
                    evaluation?.overall_score !== undefined && evaluation.overall_score !== null ? (
                      <span className="cr-step-score">
                        Score: <strong>{evaluation.overall_score.toFixed(1)}</strong>
                      </span>
                    ) : (
                      <span className="cr-step-pending">Pending</span>
                    )
                  ) : agentExec ? (
                    <>
                      <span className="cr-step-duration">
                        <Clock size={10} /> {formatDuration(agentExec.duration_seconds)}
                      </span>
                      {agentExec.findings_count > 0 && (
                        <span className="cr-step-findings-pill" title={`${agentExec.findings_count} findings discovered`}>
                          <AlertTriangle size={10} /> {agentExec.findings_count}
                        </span>
                      )}
                      <span className="cr-step-iter">Iter {agentExec.iteration}</span>
                    </>
                  ) : (
                    <span className="cr-step-pending">Not started</span>
                  )}
                </div>
              </div>

              {idx < STEPS.length - 1 && (
                <div className="cr-pipeline-connector">
                  <ArrowRight size={14} />
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
