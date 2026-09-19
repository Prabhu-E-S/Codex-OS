import React, { useState } from 'react';
import {
  X,
  Clock,
  FolderGit2,
  Box,
  AlertTriangle,
  Copy,
  Check,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
} from 'lucide-react';
import { ControlRoomAgent } from '../../api/types';

interface AgentDetailDrawerProps {
  agent: ControlRoomAgent | null;
  onClose: () => void;
}

export const AgentDetailDrawer: React.FC<AgentDetailDrawerProps> = ({ agent, onClose }) => {
  const [copied, setCopied] = useState(false);

  if (!agent) return null;

  const handleCopyOutput = () => {
    if (agent.output) {
      navigator.clipboard.writeText(agent.output);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const formatDuration = (sec?: number | null) => {
    if (sec === undefined || sec === null) return '—';
    if (sec < 1) return '<1s';
    return `${Math.round(sec)}s`;
  };

  return (
    <div className="cr-drawer-backdrop" onClick={onClose}>
      <div className="cr-drawer-content" onClick={(e) => e.stopPropagation()}>
        <div className="cr-drawer-header">
          <div className="cr-drawer-title-area">
            <h3 className="cr-drawer-title">{agent.agent_name}</h3>
            <span className="cr-drawer-type-tag">{agent.agent_type}</span>
            <span className={`cr-step-status-pill status-${agent.status.toLowerCase()}`}>
              {agent.status === 'COMPLETED' && <CheckCircle2 size={11} />}
              {agent.status === 'RUNNING' && <PlayCircle size={11} />}
              {agent.status === 'FAILED' && <AlertCircle size={11} />}
              <span>{agent.status}</span>
            </span>
          </div>

          <button className="btn-icon" onClick={onClose} title="Close drawer">
            <X size={16} />
          </button>
        </div>

        <div className="cr-drawer-body">
          {/* Metadata Grid */}
          <div className="cr-drawer-grid">
            <div className="cr-drawer-meta-item">
              <span className="meta-label">Iteration</span>
              <span className="meta-value">Iteration {agent.iteration}</span>
            </div>

            <div className="cr-drawer-meta-item">
              <span className="meta-label">Execution Duration</span>
              <span className="meta-value">
                <Clock size={12} /> {formatDuration(agent.duration_seconds)}
              </span>
            </div>

            <div className="cr-drawer-meta-item">
              <span className="meta-label">Workspace</span>
              <span className="meta-value">
                <FolderGit2 size={12} /> {agent.workspace_name || 'Not assigned'}
              </span>
            </div>

            <div className="cr-drawer-meta-item">
              <span className="meta-label">Sandbox Status</span>
              <span className="meta-value">
                <Box size={12} /> {agent.sandbox_status || 'Unavailable'}
              </span>
            </div>

            {agent.exit_code !== undefined && agent.exit_code !== null && (
              <div className="cr-drawer-meta-item">
                <span className="meta-label">Exit Code</span>
                <span className="meta-value font-mono">{agent.exit_code}</span>
              </div>
            )}

            {agent.findings_count > 0 && (
              <div className="cr-drawer-meta-item">
                <span className="meta-label">Discovered Findings</span>
                <span className="meta-value text-amber">
                  <AlertTriangle size={12} /> {agent.findings_count} findings
                </span>
              </div>
            )}
          </div>

          {/* Error notice if failed */}
          {agent.error_message && (
            <div className="cr-drawer-error-box">
              <div className="error-title">
                <AlertCircle size={14} /> Execution Error
              </div>
              <p className="error-body">{agent.error_message}</p>
            </div>
          )}

          {/* Input Summary */}
          {agent.input_summary && (
            <div className="cr-drawer-section">
              <h4 className="section-title">Input Summary</h4>
              <p className="cr-input-summary-text">{agent.input_summary}</p>
            </div>
          )}

          {/* Output Viewer */}
          <div className="cr-drawer-section cr-output-section">
            <div className="section-header">
              <h4 className="section-title">Agent Execution Output</h4>
              <button
                className="btn btn-secondary btn-xs"
                onClick={handleCopyOutput}
                disabled={!agent.output}
                title="Copy output"
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
                <span>{copied ? 'Copied' : 'Copy'}</span>
              </button>
            </div>

            {agent.output ? (
              <pre className="cr-output-pre">
                <code>{agent.output}</code>
              </pre>
            ) : (
              <div className="cr-output-empty">No output recorded for this agent execution.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
