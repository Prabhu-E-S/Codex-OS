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
  Compass,
  Hammer,
  CheckCheck,
  Bot,
  ChevronDown,
  ChevronRight,
  Box,
} from 'lucide-react';
import { EngineeringRun, RunLogsResponse, AgentExecution } from '../api/types';
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
  const [agents, setAgents] = useState<AgentExecution[]>([]);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [executingAgentTeam, setExecutingAgentTeam] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [expandedAgentId, setExpandedAgentId] = useState<number | null>(null);

  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll when logs change during active execution
  useEffect(() => {
    if (run && (run.status === 'RUNNING' || run.status === 'STARTING')) {
      terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, run]);

  // Fetch latest logs, status, and agent executions
  const fetchLogsAndStatus = async (runId: number) => {
    try {
      const [logsData, updatedRun, agentList] = await Promise.all([
        api.getRunLogs(runId),
        api.getRun(runId),
        api.getRunAgents(runId).catch(() => []),
      ]);
      setLogs(logsData);
      setAgents(agentList);
      onRunUpdated(updatedRun);
    } catch (err) {
      console.error('Failed to fetch run logs and agents:', err);
    }
  };

  // Initial load when modal opens
  useEffect(() => {
    if (isOpen && run) {
      setLoadingLogs(true);
      setLoadingAgents(true);
      fetchLogsAndStatus(run.id).finally(() => {
        setLoadingLogs(false);
        setLoadingAgents(false);
      });
    } else {
      setLogs(null);
      setAgents([]);
      setExpandedAgentId(null);
    }
  }, [isOpen, run?.id]);

  // Polling while run or agent workflow is active
  useEffect(() => {
    if (!isOpen || !run) return;

    const isRunActive = run.status === 'STARTING' || run.status === 'RUNNING';
    const isAgentActive = agents.some(
      (a) => a.status === 'STARTING' || a.status === 'RUNNING'
    );

    if (!isRunActive && !isAgentActive) return;

    const intervalId = setInterval(() => {
      fetchLogsAndStatus(run.id);
    }, 1500);

    return () => clearInterval(intervalId);
  }, [isOpen, run?.status, run?.id, agents]);

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

  const handleStartAgentTeam = async () => {
    setExecutingAgentTeam(true);
    try {
      const resp = await api.executeAgentWorkflow(run.id);
      setAgents(resp.agents);
      await fetchLogsAndStatus(run.id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to start agent team workflow');
    } finally {
      setExecutingAgentTeam(false);
    }
  };

  const handleCancelWorkflow = async () => {
    if (!window.confirm('Are you sure you want to cancel execution?')) return;
    setCancelling(true);
    try {
      if (agents.length > 0) {
        await api.cancelAgentWorkflow(run.id);
      } else {
        await api.cancelRun(run.id);
      }
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

  const getAgentStatusBadge = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return { label: 'Completed', bg: '#ECFDF5', color: '#059669', border: '#A7F3D0' };
      case 'RUNNING':
        return { label: 'Running', bg: '#EFF6FF', color: '#2563EB', border: '#BFDBFE' };
      case 'STARTING':
        return { label: 'Starting', bg: '#FFFBEB', color: '#D97706', border: '#FDE68A' };
      case 'FAILED':
        return { label: 'Failed', bg: '#FEF2F2', color: '#DC2626', border: '#FECACA' };
      case 'CANCELLED':
        return { label: 'Cancelled', bg: '#F1F5F9', color: '#64748B', border: '#CBD5E1' };
      case 'PENDING':
      default:
        return { label: 'Pending', bg: '#F8FAFC', color: '#94A3B8', border: '#E2E8F0' };
    }
  };

  const getAgentIcon = (type: string) => {
    switch (type) {
      case 'ARCHITECT':
        return <Compass size={15} color="#2563EB" />;
      case 'BUILDER':
        return <Hammer size={15} color="#059669" />;
      case 'TESTER':
        return <CheckCheck size={15} color="#D97706" />;
      default:
        return <Bot size={15} color="#64748B" />;
    }
  };

  const stdoutText = logs?.stdout ?? run.stdout ?? '';
  const stderrText = logs?.stderr ?? run.stderr ?? '';
  const errorMessage = logs?.error_message ?? run.error_message;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="modal-dialog"
        onClick={(e) => e.stopPropagation()}
        style={{ maxWidth: '780px', maxHeight: '90vh', overflowY: 'auto' }}
      >
        <div className="modal-header">
          <div className="modal-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Terminal size={18} color="#2563EB" />
            <span>Engineering Run #{run.id}</span>
            {getStatusBadge(run.status)}
          </div>
          <button
            className="modal-close"
            onClick={onClose}
            aria-label="Close"
            id="btn-close-run-detail"
          >
            <X size={16} />
          </button>
        </div>

        <div className="modal-body" style={{ gap: '16px' }}>
          {/* Goal card */}
          <div
            style={{
              padding: '12px 14px',
              backgroundColor: '#F8FAFC',
              border: '1px solid #E2E8F0',
              borderRadius: '6px',
            }}
          >
            <div style={{ fontSize: '11px', color: '#64748B', fontWeight: 600, textTransform: 'uppercase', marginBottom: '4px' }}>
              Engineering Goal
            </div>
            <div style={{ fontSize: '13px', color: '#0F172A', fontWeight: 500, lineHeight: 1.5 }}>
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
              }}
            >
              <FolderGit2 size={15} color="#059669" style={{ flexShrink: 0 }} />
              <span>Isolated Worktree Workspace:</span>
              <strong style={{ fontFamily: 'JetBrains Mono, monospace', color: '#047857' }}>
                {run.workspace_name}
              </strong>
            </div>
          )}

          {/* AGENT TEAM PIPELINE (Phase 5) */}
          <div
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              padding: '14px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Bot size={16} color="#2563EB" />
                <span style={{ fontWeight: 600, fontSize: '13px', color: '#0F172A' }}>
                  Autonomous Agent Team
                </span>
                {loadingAgents && (
                  <RefreshCw size={11} className="spinning" color="#94A3B8" />
                )}
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 600,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    backgroundColor: '#EFF6FF',
                    color: '#2563EB',
                    border: '1px solid #BFDBFE',
                  }}
                >
                  Architect → Builder → Tester
                </span>
              </div>

              {!isActive && agents.length === 0 && (
                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleStartAgentTeam}
                  disabled={executingAgentTeam}
                  style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '5px' }}
                >
                  <Bot size={12} />
                  <span>Start Agent Team</span>
                </button>
              )}
            </div>

            {agents.length === 0 ? (
              <div style={{ fontSize: '12px', color: '#64748B', lineHeight: 1.4 }}>
                Execute this engineering goal sequentially with the autonomous team: Architect designs the plan, Builder writes the code in an isolated workspace, and Tester validates with automated test execution.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {agents.map((agent) => {
                  const badge = getAgentStatusBadge(agent.status);
                  const isExpanded = expandedAgentId === agent.id;

                  return (
                    <div
                      key={agent.id}
                      style={{
                        border: '1px solid #E2E8F0',
                        borderRadius: '6px',
                        backgroundColor: '#FFFFFF',
                        overflow: 'hidden',
                      }}
                    >
                      <div
                        onClick={() => setExpandedAgentId(isExpanded ? null : agent.id)}
                        style={{
                          padding: '10px 12px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'space-between',
                          cursor: 'pointer',
                          backgroundColor: isExpanded ? '#F8FAFC' : '#FFFFFF',
                          transition: 'background-color 0.15s ease',
                        }}
                      >
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          {isExpanded ? <ChevronDown size={14} color="#64748B" /> : <ChevronRight size={14} color="#64748B" />}
                          {getAgentIcon(agent.agent_type)}
                          <span style={{ fontSize: '12px', fontWeight: 600, color: '#0F172A' }}>
                            {agent.agent_name}
                          </span>
                          {agent.workspace_name && (
                            <span style={{ fontSize: '11px', fontFamily: 'JetBrains Mono, monospace', color: '#059669', backgroundColor: '#ECFDF5', padding: '1px 6px', borderRadius: '4px', border: '1px solid #A7F3D0' }}>
                              {agent.workspace_name}
                            </span>
                          )}
                        </div>

                        <span
                          style={{
                            fontSize: '10px',
                            fontWeight: 600,
                            padding: '2px 8px',
                            borderRadius: '9999px',
                            backgroundColor: badge.bg,
                            color: badge.color,
                            border: `1px solid ${badge.border}`,
                          }}
                        >
                          {badge.label}
                        </span>
                      </div>

                      {isExpanded && (
                        <div style={{ padding: '12px', borderTop: '1px solid #E2E8F0', backgroundColor: '#F8FAFC' }}>
                          {agent.error_message && (
                            <div className="alert-banner alert-banner-error" style={{ marginBottom: '10px', fontSize: '12px' }}>
                              {agent.error_message}
                            </div>
                          )}

                          <div style={{ display: 'flex', gap: '16px', fontSize: '11px', color: '#64748B', marginBottom: '8px' }}>
                            {agent.workspace_id && <div>Workspace ID: #{agent.workspace_id}</div>}
                            {agent.sandbox_id && (
                              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                                <Box size={11} color="#2563EB" />
                                <span>Sandbox ID: #{agent.sandbox_id}</span>
                              </div>
                            )}
                            {agent.started_at && <div>Started: {new Date(agent.started_at).toLocaleTimeString()}</div>}
                            {agent.completed_at && <div>Completed: {new Date(agent.completed_at).toLocaleTimeString()}</div>}
                          </div>

                          <div style={{ fontSize: '11px', fontWeight: 600, color: '#0F172A', marginBottom: '4px' }}>
                            Agent Output:
                          </div>
                          <div
                            style={{
                              backgroundColor: '#0F172A',
                              color: '#F8FAFC',
                              padding: '10px 12px',
                              borderRadius: '6px',
                              fontSize: '11.5px',
                              fontFamily: 'JetBrains Mono, monospace',
                              whiteSpace: 'pre-wrap',
                              maxHeight: '260px',
                              overflowY: 'auto',
                              lineHeight: 1.5,
                            }}
                          >
                            {agent.output ? agent.output : '(No output recorded)'}
                          </div>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            )}
          </div>

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
                <span>Consolidated Execution Logs</span>
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
                    ? 'Execution in progress... Live logs will stream here.'
                    : 'No output captured for this run yet.'}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Footer Actions */}
        <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', gap: '8px' }}>
            {isActive ? (
              <button
                type="button"
                className="btn btn-danger btn-sm"
                onClick={handleCancelWorkflow}
                disabled={cancelling}
                id="btn-cancel-run-modal"
              >
                <StopCircle size={13} />
                <span>{cancelling ? 'Cancelling...' : 'Cancel Execution'}</span>
              </button>
            ) : (
              <>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleStartAgentTeam}
                  disabled={executingAgentTeam || executing}
                  id="btn-start-agent-team-modal"
                >
                  <Bot size={13} />
                  <span>{executingAgentTeam ? 'Starting Agents...' : 'Run Agent Team'}</span>
                </button>

                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleStartRun}
                  disabled={executing || executingAgentTeam}
                  id="btn-execute-run-modal"
                  title="Run directly with Codex without agent decomposition"
                >
                  <PlayCircle size={13} />
                  <span>Direct Run</span>
                </button>
              </>
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
