import React from 'react';
import { ControlRoomAgent, ControlRoomOrchestration, ControlRoomEvaluation } from '../../api/types';
import {
  Compass,
  Hammer,
  CheckCheck,
  Zap,
  Lock,
  Award,
  RefreshCw,
  Scale,
} from 'lucide-react';

interface AgentGraphProps {
  agents: ControlRoomAgent[];
  orchestration?: ControlRoomOrchestration | null;
  evaluation?: ControlRoomEvaluation | null;
  onSelectAgent: (agent: ControlRoomAgent) => void;
  onSelectEvaluation?: () => void;
}

export const AgentGraph: React.FC<AgentGraphProps> = ({
  agents,
  orchestration,
  evaluation,
  onSelectAgent,
  onSelectEvaluation,
}) => {
  const currentAgent = orchestration?.current_agent;
  const lastDecision = orchestration?.last_decision;
  const iteration = orchestration?.iteration || 1;

  const getAgent = (type: string): ControlRoomAgent | undefined => {
    const list = agents.filter((a) => a.agent_type.toUpperCase() === type.toUpperCase());
    return list.length > 0 ? list[list.length - 1] : undefined;
  };

  const architect = getAgent('ARCHITECT');
  const builder = getAgent('BUILDER');
  const tester = getAgent('TESTER');
  const breaker = getAgent('BREAKER');
  const security = getAgent('SECURITY');

  const getStatusClass = (agent?: ControlRoomAgent, isActive?: boolean) => {
    if (isActive) return 'node-active';
    if (!agent) return 'node-pending';
    return `node-${agent.status.toLowerCase()}`;
  };

  const isArchitectActive = currentAgent === 'ARCHITECT';
  const isBuilderActive = currentAgent === 'BUILDER';
  const isTesterActive = currentAgent === 'TESTER';
  const isBreakerActive = currentAgent === 'BREAKER';
  const isSecurityActive = currentAgent === 'SECURITY';
  const isDecidingActive = orchestration?.state === 'DECIDING';

  return (
    <div className="cr-agent-graph-card">
      <div className="cr-card-header">
        <h3 className="cr-card-title">Autonomous Orchestration Graph</h3>
        <span className="cr-card-subtitle">
          Interactive workflow graph visualizing the self-healing retry loop
        </span>
      </div>

      <div className="cr-graph-canvas">
        {/* Architect Node (Iteration 1 only) */}
        <div className="cr-graph-column cr-col-architect">
          <div className="cr-graph-phase-label">Phase 1: Architecture</div>
          <div
            className={`cr-graph-node ${getStatusClass(architect, isArchitectActive)}`}
            onClick={() => architect && onSelectAgent(architect)}
            tabIndex={0}
            role="button"
          >
            <div className="node-icon">
              <Compass size={16} />
            </div>
            <div className="node-content">
              <span className="node-title">Architect</span>
              <span className="node-meta">
                {architect ? `${architect.status} (Iter 1)` : 'Pending'}
              </span>
            </div>
          </div>
        </div>

        {/* Arrow into Autonomous Engineering Loop */}
        <div className="cr-graph-arrow-horizontal">
          <svg width="40" height="20">
            <line x1="0" y1="10" x2="32" y2="10" stroke="var(--border-color)" strokeWidth="2" />
            <polygon points="32,6 40,10 32,14" fill="var(--border-color)" />
          </svg>
        </div>

        {/* Autonomous Loop Box */}
        <div className="cr-graph-loop-box">
          <div className="cr-loop-box-header">
            <span>Autonomous Loop (Iteration {iteration})</span>
            {lastDecision === 'RETRY_BUILDER' && (
              <span className="cr-loop-active-badge">
                <RefreshCw size={11} className="spin-slow" /> Retry Active
              </span>
            )}
          </div>

          <div className="cr-loop-inner-grid">
            {/* Builder */}
            <div
              className={`cr-graph-node ${getStatusClass(builder, isBuilderActive)}`}
              onClick={() => builder && onSelectAgent(builder)}
              tabIndex={0}
              role="button"
            >
              <div className="node-icon">
                <Hammer size={16} />
              </div>
              <div className="node-content">
                <span className="node-title">Builder</span>
                <span className="node-meta">
                  {builder ? `${builder.status} (Iter ${builder.iteration})` : 'Pending'}
                </span>
              </div>
            </div>

            <div className="cr-graph-arrow-down">↓</div>

            {/* Tester */}
            <div
              className={`cr-graph-node ${getStatusClass(tester, isTesterActive)}`}
              onClick={() => tester && onSelectAgent(tester)}
              tabIndex={0}
              role="button"
            >
              <div className="node-icon">
                <CheckCheck size={16} />
              </div>
              <div className="node-content">
                <span className="node-title">Tester</span>
                <span className="node-meta">
                  {tester ? `${tester.status} (Iter ${tester.iteration})` : 'Pending'}
                </span>
              </div>
            </div>

            <div className="cr-graph-arrow-down">↓</div>

            {/* Breaker */}
            <div
              className={`cr-graph-node ${getStatusClass(breaker, isBreakerActive)}`}
              onClick={() => breaker && onSelectAgent(breaker)}
              tabIndex={0}
              role="button"
            >
              <div className="node-icon">
                <Zap size={16} />
              </div>
              <div className="node-content">
                <span className="node-title">Breaker</span>
                <span className="node-meta">
                  {breaker ? `${breaker.status} (${breaker.findings_count} findings)` : 'Pending'}
                </span>
              </div>
            </div>

            <div className="cr-graph-arrow-down">↓</div>

            {/* Security */}
            <div
              className={`cr-graph-node ${getStatusClass(security, isSecurityActive)}`}
              onClick={() => security && onSelectAgent(security)}
              tabIndex={0}
              role="button"
            >
              <div className="node-icon">
                <Lock size={16} />
              </div>
              <div className="node-content">
                <span className="node-title">Security</span>
                <span className="node-meta">
                  {security ? `${security.status} (${security.findings_count} findings)` : 'Pending'}
                </span>
              </div>
            </div>

            <div className="cr-graph-arrow-down">↓</div>

            {/* Orchestrator Decision Node */}
            <div className={`cr-graph-node node-decision ${isDecidingActive ? 'node-active' : ''}`}>
              <div className="node-icon">
                <Scale size={16} />
              </div>
              <div className="node-content">
                <span className="node-title">Orchestrator Decision</span>
                <span className="node-meta">
                  {lastDecision || (isDecidingActive ? 'Deciding...' : 'Pending')}
                </span>
              </div>
            </div>
          </div>

          {/* Retry loop visualization curve */}
          <div className="cr-retry-loop-feedback">
            <div className="cr-retry-loop-line">
              <span className="cr-retry-label">
                <RefreshCw size={11} /> RETRY_BUILDER Feedback Loop
              </span>
            </div>
          </div>
        </div>

        {/* Arrow to Evaluation */}
        <div className="cr-graph-arrow-horizontal">
          <svg width="40" height="20">
            <line x1="0" y1="10" x2="32" y2="10" stroke="var(--border-color)" strokeWidth="2" />
            <polygon points="32,6 40,10 32,14" fill="var(--border-color)" />
          </svg>
        </div>

        {/* Evaluation Node */}
        <div className="cr-graph-column cr-col-eval">
          <div className="cr-graph-phase-label">Phase 3: Evaluation</div>
          <div
            className={`cr-graph-node ${evaluation ? 'node-completed' : 'node-pending'}`}
            onClick={onSelectEvaluation}
            tabIndex={0}
            role="button"
          >
            <div className="node-icon">
              <Award size={16} />
            </div>
            <div className="node-content">
              <span className="node-title">Engineering Score</span>
              <span className="node-meta">
                {evaluation?.overall_score !== undefined && evaluation?.overall_score !== null
                  ? `${evaluation.overall_score.toFixed(1)} / 100 (${evaluation.status_label})`
                  : 'Evaluation pending'}
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
