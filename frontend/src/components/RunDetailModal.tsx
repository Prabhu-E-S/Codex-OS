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
  Zap,
  Lock,
  ShieldAlert,
  Pause,
  Play,
  Sparkles,
  Layers,
  Award,
  Activity,
} from 'lucide-react';
import {
  EngineeringRun,
  RunLogsResponse,
  AgentExecution,
  Finding,
  FindingsSummary,
  OrchestrationResponse,
  Evaluation,
  EvaluationDimension,
} from '../api/types';
import { api } from '../api/client';

interface RunDetailModalProps {
  run: EngineeringRun | null;
  isOpen: boolean;
  onClose: () => void;
  onRunUpdated: (updatedRun: EngineeringRun) => void;
  onOpenControlRoom?: (runId: number) => void;
}

export const RunDetailModal: React.FC<RunDetailModalProps> = ({
  run,
  isOpen,
  onClose,
  onRunUpdated,
  onOpenControlRoom,
}) => {
  const [logs, setLogs] = useState<RunLogsResponse | null>(null);
  const [agents, setAgents] = useState<AgentExecution[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [findingsSummary, setFindingsSummary] = useState<FindingsSummary | null>(null);
  const [orchState, setOrchState] = useState<OrchestrationResponse | null>(null);
  const [maxIterations, setMaxIterations] = useState<number>(3);
  const [selectedIteration, setSelectedIteration] = useState<number | 'ALL'>('ALL');
  const [startingAutonomous, setStartingAutonomous] = useState(false);
  const [pausing, setPausing] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [loadingLogs, setLoadingLogs] = useState(false);
  const [loadingAgents, setLoadingAgents] = useState(false);
  const [loadingFindings, setLoadingFindings] = useState(false);
  const [executing, setExecuting] = useState(false);
  const [executingAgentTeam, setExecutingAgentTeam] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [evaluating, setEvaluating] = useState(false);
  const [loadingEvaluations, setLoadingEvaluations] = useState(false);
  const [expandedAgentId, setExpandedAgentId] = useState<number | null>(null);
  const [expandedFindingId, setExpandedFindingId] = useState<number | null>(null);
  const [findingTypeFilter, setFindingTypeFilter] = useState<'ALL' | 'BREAKER' | 'SECURITY'>('ALL');

  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll when logs change during active execution
  useEffect(() => {
    if (run && (run.status === 'RUNNING' || run.status === 'STARTING')) {
      terminalEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [logs, run]);

  // Fetch latest logs, status, agent executions, findings, orchestration state, and evaluations
  const fetchLogsAndStatus = async (runId: number) => {
    try {
      const [logsData, updatedRun, agentList, findingsList, summaryData, orchData, evalsData] = await Promise.all([
        api.getRunLogs(runId),
        api.getRun(runId),
        api.getRunAgents(runId).catch(() => []),
        api.getRunFindings(runId).catch(() => []),
        api.getRunFindingsSummary(runId).catch(() => null),
        api.getOrchestrationStatus(runId).catch(() => null),
        api.getRunEvaluations(runId).catch(() => []),
      ]);
      setLogs(logsData);
      setAgents(agentList);
      setFindings(findingsList);
      setFindingsSummary(summaryData);
      if (orchData !== null) {
        setOrchState(orchData);
      }
      setEvaluations(evalsData);
      onRunUpdated(updatedRun);
    } catch (err) {
      console.error('Failed to fetch run logs, agents, findings, and orchestration:', err);
    }
  };

  // Initial load when modal opens
  useEffect(() => {
    if (isOpen && run) {
      setLoadingLogs(true);
      setLoadingAgents(true);
      setLoadingFindings(true);
      setLoadingEvaluations(true);
      fetchLogsAndStatus(run.id).finally(() => {
        setLoadingLogs(false);
        setLoadingAgents(false);
        setLoadingFindings(false);
        setLoadingEvaluations(false);
      });
    } else {
      setLogs(null);
      setAgents([]);
      setFindings([]);
      setFindingsSummary(null);
      setOrchState(null);
      setEvaluations([]);
      setExpandedAgentId(null);
      setExpandedFindingId(null);
    }
  }, [isOpen, run?.id]);

  // Polling while run or agent workflow or autonomous loop is active
  useEffect(() => {
    if (!isOpen || !run) return;

    const isRunActive = run.status === 'STARTING' || run.status === 'RUNNING';
    const isAgentActive = agents.some(
      (a) => a.status === 'STARTING' || a.status === 'RUNNING'
    );
    const isOrchActive = orchState
      ? ['ARCHITECTING', 'BUILDING', 'TESTING', 'BREAKING', 'SECURITY_SCANNING', 'DECIDING', 'ITERATING'].includes(orchState.state)
      : false;

    if (!isRunActive && !isAgentActive && !isOrchActive) return;

    const intervalId = setInterval(() => {
      fetchLogsAndStatus(run.id);
    }, 1500);

    return () => clearInterval(intervalId);
  }, [isOpen, run?.status, run?.id, agents, orchState?.state]);

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

  const handleStartAutonomous = async () => {
    setStartingAutonomous(true);
    try {
      const resp = await api.startAutonomousRun(run.id, maxIterations);
      setOrchState(resp);
      await fetchLogsAndStatus(run.id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to start autonomous run');
    } finally {
      setStartingAutonomous(false);
    }
  };

  const handlePause = async () => {
    setPausing(true);
    try {
      const resp = await api.pauseRun(run.id);
      setOrchState(resp);
      await fetchLogsAndStatus(run.id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to pause run');
    } finally {
      setPausing(false);
    }
  };

  const handleResume = async () => {
    setResuming(true);
    try {
      const resp = await api.resumeRun(run.id);
      setOrchState(resp);
      await fetchLogsAndStatus(run.id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to resume run');
    } finally {
      setResuming(false);
    }
  };

  const handleCancelWorkflow = async () => {
    if (!window.confirm('Are you sure you want to cancel execution?')) return;
    setCancelling(true);
    try {
      if (orchState && !['COMPLETED', 'FAILED', 'CANCELLED'].includes(orchState.state)) {
        await api.cancelAutonomousRun(run.id);
      } else if (agents.length > 0) {
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

  const handleEvaluateRun = async () => {
    if (!run) return;
    setEvaluating(true);
    try {
      await api.evaluateRun(run.id);
      await fetchLogsAndStatus(run.id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to evaluate run');
    } finally {
      setEvaluating(false);
    }
  };

  const getEvaluationStatusBadge = (statusLabel?: string) => {
    switch (statusLabel) {
      case 'STRONG':
        return { bg: '#ECFDF5', color: '#065F46', border: '#A7F3D0', label: 'STRONG' };
      case 'ADEQUATE':
        return { bg: '#EFF6FF', color: '#1E40AF', border: '#BFDBFE', label: 'ADEQUATE' };
      case 'WEAK':
        return { bg: '#FEF2F2', color: '#991B1B', border: '#FECACA', label: 'WEAK' };
      case 'INSUFFICIENT_EVIDENCE':
      default:
        return { bg: '#F1F5F9', color: '#475569', border: '#CBD5E1', label: 'INSUFFICIENT EVIDENCE' };
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

  const getSeverityBadgeStyle = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'CRITICAL':
        return { bg: '#FEF2F2', color: '#DC2626', border: '#FECACA' };
      case 'HIGH':
        return { bg: '#FFF7ED', color: '#EA580C', border: '#FFEDD5' };
      case 'MEDIUM':
        return { bg: '#FFFBEB', color: '#D97706', border: '#FDE68A' };
      case 'LOW':
        return { bg: '#EFF6FF', color: '#2563EB', border: '#BFDBFE' };
      case 'INFO':
      default:
        return { bg: '#F8FAFC', color: '#64748B', border: '#E2E8F0' };
    }
  };

  const getWorkflowStateBadge = (state: string) => {
    switch (state) {
      case 'COMPLETED':
        return { label: 'COMPLETED', bg: '#ECFDF5', color: '#059669', border: '#A7F3D0' };
      case 'BUILDING':
      case 'TESTING':
      case 'BREAKING':
      case 'SECURITY_SCANNING':
      case 'ARCHITECTING':
      case 'ITERATING':
      case 'DECIDING':
        return { label: state, bg: '#EFF6FF', color: '#2563EB', border: '#BFDBFE' };
      case 'PAUSED':
        return { label: 'PAUSED', bg: '#FFFBEB', color: '#D97706', border: '#FDE68A' };
      case 'CANCELLED':
        return { label: 'CANCELLED', bg: '#F1F5F9', color: '#64748B', border: '#CBD5E1' };
      case 'FAILED':
        return { label: 'FAILED', bg: '#FEF2F2', color: '#DC2626', border: '#FECACA' };
      default:
        return { label: state, bg: '#F8FAFC', color: '#64748B', border: '#E2E8F0' };
    }
  };

  const getDecisionBadge = (decision: string) => {
    switch (decision) {
      case 'STOP_SUCCESS':
        return { label: 'Complete (Success)', bg: '#ECFDF5', color: '#059669', border: '#A7F3D0' };
      case 'RETRY_BUILDER':
        return { label: 'Retry Builder', bg: '#FFFBEB', color: '#D97706', border: '#FDE68A' };
      case 'STOP_FAILURE':
        return { label: 'Halted (Failure)', bg: '#FEF2F2', color: '#DC2626', border: '#FECACA' };
      case 'PAUSE':
        return { label: 'Paused', bg: '#EFF6FF', color: '#2563EB', border: '#BFDBFE' };
      case 'CANCELLED':
        return { label: 'Cancelled', bg: '#F1F5F9', color: '#64748B', border: '#CBD5E1' };
      default:
        return { label: decision, bg: '#F8FAFC', color: '#64748B', border: '#E2E8F0' };
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
      case 'BREAKER':
        return <Zap size={15} color="#DC2626" />;
      case 'SECURITY':
        return <Lock size={15} color="#7C3AED" />;
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
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginLeft: 'auto' }}>
            {onOpenControlRoom && (
              <button
                className="btn btn-secondary btn-xs"
                onClick={() => {
                  onClose();
                  onOpenControlRoom(run.id);
                }}
                title="Observe this run in the Control Room"
                style={{ display: 'inline-flex', alignItems: 'center', gap: '5px' }}
              >
                <Activity size={13} color="#2563EB" />
                <span>Open in Control Room</span>
              </button>
            )}
            <button
              className="modal-close"
              onClick={onClose}
              aria-label="Close"
              id="btn-close-run-detail"
            >
              <X size={16} />
            </button>
          </div>
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

          {/* AUTONOMOUS ORCHESTRATOR PANEL (Phase 7) */}
          <div
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              padding: '14px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px', flexWrap: 'wrap', gap: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                <Sparkles size={16} color="#2563EB" />
                <span style={{ fontWeight: 600, fontSize: '13px', color: '#0F172A' }}>
                  Autonomous Orchestrator
                </span>
                {orchState && (
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 600,
                      padding: '2px 8px',
                      borderRadius: '9999px',
                      backgroundColor: getWorkflowStateBadge(orchState.state).bg,
                      color: getWorkflowStateBadge(orchState.state).color,
                      border: `1px solid ${getWorkflowStateBadge(orchState.state).border}`,
                    }}
                  >
                    {orchState.state}
                  </span>
                )}
                {orchState && (
                  <span
                    style={{
                      fontSize: '11px',
                      fontWeight: 500,
                      color: '#475569',
                      backgroundColor: '#F1F5F9',
                      padding: '1px 7px',
                      borderRadius: '4px',
                      border: '1px solid #CBD5E1',
                    }}
                  >
                    Iteration {orchState.iteration} of {orchState.max_iterations}
                  </span>
                )}
                {orchState?.current_agent && (
                  <span style={{ fontSize: '11px', color: '#2563EB', fontWeight: 500 }}>
                    Active: {orchState.current_agent}
                  </span>
                )}
              </div>

              {/* Boundary Controls if active or paused */}
              {orchState && !['COMPLETED', 'FAILED', 'CANCELLED'].includes(orchState.state) && (
                <div style={{ display: 'flex', gap: '6px' }}>
                  {orchState.state === 'PAUSED' ? (
                    <button
                      className="btn btn-primary btn-sm"
                      onClick={handleResume}
                      disabled={resuming}
                      style={{ fontSize: '11px', padding: '3px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      <Play size={12} />
                      <span>{resuming ? 'Resuming...' : 'Resume Run'}</span>
                    </button>
                  ) : (
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={handlePause}
                      disabled={pausing || orchState.pause_requested}
                      style={{ fontSize: '11px', padding: '3px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}
                    >
                      <Pause size={12} />
                      <span>{orchState.pause_requested ? 'Pausing...' : 'Pause at Boundary'}</span>
                    </button>
                  )}
                </div>
              )}
            </div>

            {orchState?.pause_requested && orchState.state !== 'PAUSED' && (
              <div
                style={{
                  marginBottom: '10px',
                  padding: '6px 10px',
                  backgroundColor: '#FFFBEB',
                  border: '1px solid #FDE68A',
                  borderRadius: '4px',
                  fontSize: '11px',
                  color: '#92400E',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                }}
              >
                <Clock size={13} color="#D97706" />
                <span>Pause requested. Execution will safely pause as soon as the current agent completes.</span>
              </div>
            )}

            {/* Last decision banner if available */}
            {orchState?.last_decision && (
              <div
                style={{
                  marginBottom: '10px',
                  padding: '8px 10px',
                  backgroundColor: '#F8FAFC',
                  border: '1px solid #E2E8F0',
                  borderRadius: '6px',
                  fontSize: '12px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '3px', flexWrap: 'wrap' }}>
                  <span style={{ fontSize: '11px', color: '#64748B', fontWeight: 600 }}>ORCHESTRATION DECISION:</span>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 600,
                      padding: '1px 6px',
                      borderRadius: '4px',
                      backgroundColor: getDecisionBadge(orchState.last_decision).bg,
                      color: getDecisionBadge(orchState.last_decision).color,
                      border: `1px solid ${getDecisionBadge(orchState.last_decision).border}`,
                    }}
                  >
                    {getDecisionBadge(orchState.last_decision).label}
                  </span>
                </div>
                <div style={{ color: '#0F172A', fontSize: '12px', lineHeight: 1.4 }}>
                  {orchState.last_decision_reason}
                </div>
              </div>
            )}

            {/* Autonomous execution starter controls */}
            {!isActive && (!orchState || ['COMPLETED', 'FAILED', 'CANCELLED'].includes(orchState.state)) && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '10px 12px',
                  backgroundColor: '#F8FAFC',
                  border: '1px solid #E2E8F0',
                  borderRadius: '6px',
                  flexWrap: 'wrap',
                  gap: '8px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ fontSize: '12px', color: '#475569', fontWeight: 500 }}>Maximum Iterations:</span>
                  <input
                    type="number"
                    min={1}
                    max={10}
                    value={maxIterations}
                    onChange={(e) => setMaxIterations(Math.max(1, Math.min(10, parseInt(e.target.value) || 1)))}
                    style={{
                      width: '50px',
                      padding: '3px 6px',
                      fontSize: '12px',
                      borderRadius: '4px',
                      border: '1px solid #CBD5E1',
                      textAlign: 'center',
                    }}
                  />
                  <span style={{ fontSize: '11px', color: '#94A3B8' }}>(1–10 loops)</span>
                </div>

                <button
                  className="btn btn-primary btn-sm"
                  onClick={handleStartAutonomous}
                  disabled={startingAutonomous || executing || executingAgentTeam}
                  style={{ fontSize: '11px', padding: '5px 12px', display: 'flex', alignItems: 'center', gap: '5px' }}
                >
                  <Sparkles size={12} />
                  <span>{startingAutonomous ? 'Starting Orchestrator...' : 'Start Autonomous Run'}</span>
                </button>
              </div>
            )}
          </div>

          {/* AGENT TEAM PIPELINE & MULTI-ITERATION TIMELINE */}
          {(() => {
            const distinctIterations = Array.from(new Set(agents.map((a) => a.iteration || 1))).sort((a, b) => a - b);

            const renderAgentCard = (agent: AgentExecution) => {
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
                    marginBottom: '6px',
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
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                      {isExpanded ? <ChevronDown size={14} color="#64748B" /> : <ChevronRight size={14} color="#64748B" />}
                      {getAgentIcon(agent.agent_type)}
                      <span style={{ fontSize: '12px', fontWeight: 600, color: '#0F172A' }}>
                        {agent.agent_name}
                      </span>
                      {agent.iteration && distinctIterations.length > 1 && (
                        <span style={{ fontSize: '10px', color: '#64748B', backgroundColor: '#F1F5F9', padding: '1px 5px', borderRadius: '3px' }}>
                          Iter {agent.iteration}
                        </span>
                      )}
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

                      <div style={{ display: 'flex', gap: '16px', fontSize: '11px', color: '#64748B', marginBottom: '8px', flexWrap: 'wrap' }}>
                        <div>Iteration: #{agent.iteration || 1}</div>
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
            };

            return (
              <div
                style={{
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #E2E8F0',
                  borderRadius: '8px',
                  padding: '14px',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Bot size={16} color="#2563EB" />
                    <span style={{ fontWeight: 600, fontSize: '13px', color: '#0F172A' }}>
                      Agent Team Execution
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
                      Architect → Builder → Tester → Breaker → Security
                    </span>
                  </div>

                  {!isActive && agents.length === 0 && (
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={handleStartAgentTeam}
                      disabled={executingAgentTeam}
                      style={{ fontSize: '11px', padding: '4px 10px', display: 'flex', alignItems: 'center', gap: '5px' }}
                    >
                      <Bot size={12} />
                      <span>Start Agent Team (Single Pass)</span>
                    </button>
                  )}
                </div>

                {agents.length === 0 ? (
                  <div style={{ fontSize: '12px', color: '#64748B', lineHeight: 1.4 }}>
                    Execute this engineering goal sequentially with the autonomous team: Architect designs the plan, Builder writes code, Tester validates, Breaker analyzes edge cases, and Security scans vulnerabilities.
                  </div>
                ) : distinctIterations.length > 1 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {distinctIterations.map((iterNum) => {
                      const iterAgents = agents.filter((a) => (a.iteration || 1) === iterNum);
                      const iterDecisionEvt = orchState?.events?.find(
                        (e) => e.iteration === iterNum && e.event_type === 'decision.made'
                      );

                      return (
                        <div
                          key={iterNum}
                          style={{
                            border: '1px solid #E2E8F0',
                            borderRadius: '6px',
                            padding: '10px 12px',
                            backgroundColor: '#FAFAFA',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                              <Layers size={14} color="#2563EB" />
                              <span style={{ fontSize: '12px', fontWeight: 700, color: '#0F172A' }}>
                                Iteration {iterNum}
                              </span>
                              <span style={{ fontSize: '11px', color: '#64748B' }}>({iterAgents.length} executions)</span>
                            </div>

                            {iterDecisionEvt && iterDecisionEvt.decision && (
                              <span
                                style={{
                                  fontSize: '10px',
                                  fontWeight: 600,
                                  padding: '2px 8px',
                                  borderRadius: '9999px',
                                  backgroundColor: getDecisionBadge(iterDecisionEvt.decision).bg,
                                  color: getDecisionBadge(iterDecisionEvt.decision).color,
                                  border: `1px solid ${getDecisionBadge(iterDecisionEvt.decision).border}`,
                                }}
                              >
                                {getDecisionBadge(iterDecisionEvt.decision).label}
                              </span>
                            )}
                          </div>

                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            {iterAgents.map(renderAgentCard)}
                          </div>

                          {iterDecisionEvt && iterDecisionEvt.reason && (
                            <div
                              style={{
                                marginTop: '6px',
                                padding: '6px 8px',
                                backgroundColor: '#FFFFFF',
                                border: '1px solid #E2E8F0',
                                borderRadius: '4px',
                                fontSize: '11px',
                                color: '#475569',
                              }}
                            >
                              <strong>Decision:</strong> {iterDecisionEvt.reason}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    {agents.map(renderAgentCard)}
                  </div>
                )}
              </div>
            );
          })()}

          {/* ADVERSARIAL & SECURITY FINDINGS (Phase 6 & Phase 7 Multi-Iteration) */}
          {(() => {
            const distinctFindingIters = Array.from(
              new Set(findings.map((f) => f.iteration || 1))
            ).sort((a, b) => a - b);

            const filteredFindings = findings.filter((f) => {
              if (findingTypeFilter === 'BREAKER' && f.type !== 'BREAKER') return false;
              if (findingTypeFilter === 'SECURITY' && f.type !== 'SECURITY') return false;
              if (selectedIteration !== 'ALL' && (f.iteration || 1) !== selectedIteration) return false;
              return true;
            });

            const breakerCount = findings.filter((f) => f.type === 'BREAKER').length;
            const securityCount = findings.filter((f) => f.type === 'SECURITY').length;
            const critHighCount = findings.filter(
              (f) => f.severity === 'CRITICAL' || f.severity === 'HIGH'
            ).length;

            return (
              <div
                style={{
                  backgroundColor: '#FFFFFF',
                  border: '1px solid #E2E8F0',
                  borderRadius: '8px',
                  padding: '14px',
                  boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
                }}
              >
                {/* Header */}
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '12px',
                    flexWrap: 'wrap',
                    gap: '8px',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <ShieldAlert size={16} color="#DC2626" />
                    <span style={{ fontWeight: 600, fontSize: '13px', color: '#0F172A' }}>
                      Adversarial & Security Findings
                    </span>
                    {loadingFindings && (
                      <RefreshCw size={11} className="spinning" color="#94A3B8" />
                    )}
                    <span
                      style={{
                        fontSize: '10px',
                        fontWeight: 600,
                        padding: '2px 6px',
                        borderRadius: '4px',
                        backgroundColor: '#FEF2F2',
                        color: '#DC2626',
                        border: '1px solid #FECACA',
                      }}
                    >
                      Phase 6
                    </span>
                  </div>

                  {/* Filter Pills */}
                  <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
                    {distinctFindingIters.length > 1 && (
                      <div style={{ display: 'flex', gap: '3px', alignItems: 'center' }}>
                        <span style={{ fontSize: '10px', color: '#64748B', fontWeight: 600 }}>Iter:</span>
                        <button
                          type="button"
                          onClick={() => setSelectedIteration('ALL')}
                          style={{
                            fontSize: '10px',
                            fontWeight: 500,
                            padding: '2px 6px',
                            borderRadius: '4px',
                            border: selectedIteration === 'ALL' ? '1px solid #7C3AED' : '1px solid #E2E8F0',
                            backgroundColor: selectedIteration === 'ALL' ? '#F5F3FF' : '#FFFFFF',
                            color: selectedIteration === 'ALL' ? '#7C3AED' : '#64748B',
                            cursor: 'pointer',
                          }}
                        >
                          All
                        </button>
                        {distinctFindingIters.map((it) => (
                          <button
                            key={it}
                            type="button"
                            onClick={() => setSelectedIteration(it)}
                            style={{
                              fontSize: '10px',
                              fontWeight: 500,
                              padding: '2px 6px',
                              borderRadius: '4px',
                              border: selectedIteration === it ? '1px solid #7C3AED' : '1px solid #E2E8F0',
                              backgroundColor: selectedIteration === it ? '#F5F3FF' : '#FFFFFF',
                              color: selectedIteration === it ? '#7C3AED' : '#64748B',
                              cursor: 'pointer',
                            }}
                          >
                            Iter {it}
                          </button>
                        ))}
                      </div>
                    )}

                    <div style={{ display: 'flex', gap: '4px' }}>
                      {(['ALL', 'BREAKER', 'SECURITY'] as const).map((tab) => (
                        <button
                          key={tab}
                          type="button"
                          onClick={() => setFindingTypeFilter(tab)}
                          style={{
                            fontSize: '11px',
                            fontWeight: 500,
                            padding: '3px 8px',
                            borderRadius: '4px',
                            border: findingTypeFilter === tab ? '1px solid #2563EB' : '1px solid #E2E8F0',
                            backgroundColor: findingTypeFilter === tab ? '#EFF6FF' : '#FFFFFF',
                            color: findingTypeFilter === tab ? '#2563EB' : '#64748B',
                            cursor: 'pointer',
                          }}
                        >
                          {tab === 'ALL'
                            ? `All (${findings.length})`
                            : tab === 'BREAKER'
                            ? `Breaker (${breakerCount})`
                            : `Security (${securityCount})`}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Metrics Overview Cards */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                    gap: '8px',
                    marginBottom: '12px',
                  }}
                >
                  <div
                    style={{
                      padding: '8px 10px',
                      backgroundColor: '#F8FAFC',
                      border: '1px solid #E2E8F0',
                      borderRadius: '6px',
                    }}
                  >
                    <div style={{ fontSize: '10px', color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>
                      Total Findings
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: '#0F172A' }}>
                      {findings.length}
                    </div>
                  </div>
                  <div
                    style={{
                      padding: '8px 10px',
                      backgroundColor: '#FEF2F2',
                      border: '1px solid #FECACA',
                      borderRadius: '6px',
                    }}
                  >
                    <div style={{ fontSize: '10px', color: '#DC2626', fontWeight: 600, textTransform: 'uppercase' }}>
                      Breaker (Adversarial)
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: '#DC2626' }}>
                      {breakerCount}
                    </div>
                  </div>
                  <div
                    style={{
                      padding: '8px 10px',
                      backgroundColor: '#F5F3FF',
                      border: '1px solid #DDD6FE',
                      borderRadius: '6px',
                    }}
                  >
                    <div style={{ fontSize: '10px', color: '#7C3AED', fontWeight: 600, textTransform: 'uppercase' }}>
                      Security (Audit)
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: '#7C3AED' }}>
                      {securityCount}
                    </div>
                  </div>
                  <div
                    style={{
                      padding: '8px 10px',
                      backgroundColor: '#FFF7ED',
                      border: '1px solid #FFEDD5',
                      borderRadius: '6px',
                    }}
                  >
                    <div style={{ fontSize: '10px', color: '#EA580C', fontWeight: 600, textTransform: 'uppercase' }}>
                      Critical / High
                    </div>
                    <div style={{ fontSize: '16px', fontWeight: 700, color: '#EA580C' }}>
                      {critHighCount}
                    </div>
                  </div>
                </div>

                {/* Category Tags Breakdown */}
                {findingsSummary && Object.keys(findingsSummary.by_category).length > 0 && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap', marginBottom: '12px' }}>
                    <span style={{ fontSize: '11px', color: '#64748B', fontWeight: 500 }}>Categories:</span>
                    {Object.entries(findingsSummary.by_category).map(([cat, count]) => (
                      <span
                        key={cat}
                        style={{
                          fontSize: '10px',
                          padding: '1px 6px',
                          borderRadius: '4px',
                          backgroundColor: '#F1F5F9',
                          border: '1px solid #E2E8F0',
                          color: '#475569',
                          fontFamily: 'JetBrains Mono, monospace',
                        }}
                      >
                        {cat} ({count})
                      </span>
                    ))}
                  </div>
                )}

                {/* Findings List */}
                {filteredFindings.length === 0 ? (
                  <div
                    style={{
                      padding: '12px',
                      textAlign: 'center',
                      fontSize: '12px',
                      color: '#64748B',
                      backgroundColor: '#F8FAFC',
                      borderRadius: '6px',
                      border: '1px solid #E2E8F0',
                    }}
                  >
                    {findings.length === 0
                      ? 'No adversarial or security weaknesses found yet. Run the autonomous agent team to perform Breaker and Security audits.'
                      : `No findings matching filter "${findingTypeFilter}".`}
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {filteredFindings.map((finding) => {
                      const isExpanded = expandedFindingId === finding.id;
                      const sevStyle = getSeverityBadgeStyle(finding.severity);

                      return (
                        <div
                          key={finding.id}
                          style={{
                            border: '1px solid #E2E8F0',
                            borderRadius: '6px',
                            backgroundColor: '#FFFFFF',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            onClick={() => setExpandedFindingId(isExpanded ? null : finding.id)}
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
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                              {isExpanded ? (
                                <ChevronDown size={14} color="#64748B" />
                              ) : (
                                <ChevronRight size={14} color="#64748B" />
                              )}

                              {/* Severity Badge */}
                              <span
                                style={{
                                  fontSize: '10px',
                                  fontWeight: 700,
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  backgroundColor: sevStyle.bg,
                                  color: sevStyle.color,
                                  border: `1px solid ${sevStyle.border}`,
                                }}
                              >
                                {finding.severity}
                              </span>

                              {/* Type Badge */}
                              <span
                                style={{
                                  fontSize: '10px',
                                  fontWeight: 600,
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  backgroundColor: finding.type === 'BREAKER' ? '#FEF2F2' : '#F5F3FF',
                                  color: finding.type === 'BREAKER' ? '#DC2626' : '#7C3AED',
                                  border: `1px solid ${
                                    finding.type === 'BREAKER' ? '#FECACA' : '#DDD6FE'
                                  }`,
                                }}
                              >
                                {finding.type}
                              </span>

                              {/* Iteration Badge */}
                              <span
                                style={{
                                  fontSize: '10px',
                                  fontWeight: 600,
                                  padding: '2px 6px',
                                  borderRadius: '4px',
                                  backgroundColor: '#F1F5F9',
                                  color: '#475569',
                                  border: '1px solid #CBD5E1',
                                }}
                              >
                                Iter {finding.iteration || 1}
                              </span>

                              {/* Title */}
                              <span style={{ fontSize: '12px', fontWeight: 600, color: '#0F172A' }}>
                                {finding.title}
                              </span>

                              {/* File & Line */}
                              {finding.file_path && (
                                <span
                                  style={{
                                    fontSize: '11px',
                                    fontFamily: 'JetBrains Mono, monospace',
                                    color: '#64748B',
                                    backgroundColor: '#F1F5F9',
                                    padding: '1px 6px',
                                    borderRadius: '4px',
                                    border: '1px solid #E2E8F0',
                                  }}
                                >
                                  {finding.file_path}
                                  {finding.line_number ? `:${finding.line_number}` : ''}
                                </span>
                              )}
                            </div>

                            <span
                              style={{
                                fontSize: '10px',
                                fontWeight: 600,
                                color: '#64748B',
                                textTransform: 'uppercase',
                                letterSpacing: '0.04em',
                              }}
                            >
                              {finding.category}
                            </span>
                          </div>

                          {isExpanded && (
                            <div
                              style={{
                                padding: '12px',
                                borderTop: '1px solid #E2E8F0',
                                backgroundColor: '#F8FAFC',
                                fontSize: '12px',
                              }}
                            >
                              <div style={{ marginBottom: '8px', color: '#334155', lineHeight: 1.5 }}>
                                <strong>Description: </strong>
                                {finding.description}
                              </div>

                              {finding.evidence && (
                                <div style={{ marginBottom: '8px' }}>
                                  <div
                                    style={{
                                      fontSize: '11px',
                                      fontWeight: 600,
                                      color: '#0F172A',
                                      marginBottom: '4px',
                                    }}
                                  >
                                    Evidence:
                                  </div>
                                  <div
                                    style={{
                                      backgroundColor: '#0F172A',
                                      color: '#F8FAFC',
                                      padding: '8px 10px',
                                      borderRadius: '6px',
                                      fontSize: '11px',
                                      fontFamily: 'JetBrains Mono, monospace',
                                      whiteSpace: 'pre-wrap',
                                      lineHeight: 1.4,
                                    }}
                                  >
                                    {finding.evidence}
                                  </div>
                                </div>
                              )}

                              {finding.reproduction && (
                                <div style={{ marginBottom: '8px', color: '#475569' }}>
                                  <strong style={{ color: '#0F172A' }}>Reproduction: </strong>
                                  <span
                                    style={{
                                      fontFamily: 'JetBrains Mono, monospace',
                                      fontSize: '11.5px',
                                      color: '#0369A1',
                                    }}
                                  >
                                    {finding.reproduction}
                                  </span>
                                </div>
                              )}

                              {finding.remediation && (
                                <div
                                  style={{
                                    padding: '8px 10px',
                                    backgroundColor: '#ECFDF5',
                                    border: '1px solid #A7F3D0',
                                    borderRadius: '6px',
                                    color: '#065F46',
                                  }}
                                >
                                  <strong>Remediation: </strong>
                                  {finding.remediation}
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })()}

          {/* ENGINEERING EVALUATION & SCORE (Phase 8) */}
          <div
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              padding: '14px',
              boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
            }}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '10px',
                flexWrap: 'wrap',
                gap: '8px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Award size={16} color="#7C3AED" />
                <span style={{ fontWeight: 600, fontSize: '13px', color: '#0F172A' }}>
                  Engineering Evaluation & Score
                </span>
                {loadingEvaluations && (
                  <RefreshCw size={11} className="spinning" color="#94A3B8" />
                )}
                <span
                  style={{
                    fontSize: '10px',
                    fontWeight: 600,
                    padding: '2px 6px',
                    borderRadius: '4px',
                    backgroundColor: '#F5F3FF',
                    color: '#7C3AED',
                    border: '1px solid #DDD6FE',
                  }}
                >
                  Phase 8
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {evaluations.length > 0 ? (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={handleEvaluateRun}
                    disabled={evaluating}
                    style={{ fontSize: '11px', padding: '3px 8px', display: 'flex', alignItems: 'center', gap: '4px' }}
                  >
                    <RefreshCw size={11} className={evaluating ? 'spinning' : ''} />
                    <span>{evaluating ? 'Evaluating...' : 'Re-evaluate'}</span>
                  </button>
                ) : (
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={handleEvaluateRun}
                    disabled={evaluating || isActive}
                    style={{
                      fontSize: '11px',
                      padding: '3px 10px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      backgroundColor: '#7C3AED',
                      borderColor: '#6D28D9',
                    }}
                  >
                    <Award size={12} />
                    <span>{evaluating ? 'Evaluating...' : 'Evaluate Run'}</span>
                  </button>
                )}
              </div>
            </div>

            {evaluations.length === 0 ? (
              <div style={{ fontSize: '12px', color: '#64748B', lineHeight: 1.4 }}>
                Produce an evidence-backed Engineering Score across Correctness, Coverage, Security, Maintainability, Performance, and Regression Risk. Click &ldquo;Evaluate Run&rdquo; to evaluate this run.
              </div>
            ) : (() => {
              const latestEval = evaluations[0];
              const statusStyle = getEvaluationStatusBadge(latestEval.status_label);

              return (
                <div>
                  {/* Top Score Summary */}
                  <div
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '10px 14px',
                      backgroundColor: '#F8FAFC',
                      borderRadius: '6px',
                      border: '1px solid #E2E8F0',
                      marginBottom: '10px',
                      flexWrap: 'wrap',
                      gap: '8px',
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px' }}>
                      <span style={{ fontSize: '24px', fontWeight: 800, color: '#0F172A', lineHeight: 1 }}>
                        {latestEval.overall_score !== null && latestEval.overall_score !== undefined
                          ? latestEval.overall_score.toFixed(1)
                          : '—'}
                      </span>
                      <span style={{ fontSize: '13px', color: '#64748B', fontWeight: 500 }}>/ 100</span>
                      <span
                        style={{
                          fontSize: '10px',
                          fontWeight: 700,
                          padding: '1px 6px',
                          borderRadius: '4px',
                          backgroundColor: statusStyle.bg,
                          color: statusStyle.color,
                          border: `1px solid ${statusStyle.border}`,
                        }}
                      >
                        {statusStyle.label}
                      </span>
                      <span style={{ fontSize: '11px', color: '#64748B', marginLeft: '6px' }}>
                        (Version {latestEval.score_version})
                      </span>
                    </div>

                    <div style={{ fontSize: '11px', color: '#64748B' }}>
                      {evaluations.length > 1 ? `${evaluations.length} historical evaluations` : '1 evaluation record'}
                    </div>
                  </div>

                  {/* Formula Preview */}
                  {latestEval.formula && (
                    <div
                      style={{
                        padding: '6px 10px',
                        backgroundColor: '#FFFFFF',
                        border: '1px solid #E2E8F0',
                        borderRadius: '4px',
                        fontSize: '11px',
                        fontFamily: 'JetBrains Mono, monospace',
                        color: '#334155',
                        marginBottom: '10px',
                        overflowX: 'auto',
                      }}
                    >
                      {latestEval.formula}
                    </div>
                  )}

                  {/* Dimensions Mini Grid */}
                  {latestEval.dimensions && latestEval.dimensions.length > 0 && (
                    <div
                      style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
                        gap: '6px',
                      }}
                    >
                      {latestEval.dimensions.map((d: EvaluationDimension) => (
                        <div
                          key={d.id}
                          style={{
                            padding: '6px 8px',
                            backgroundColor: '#FFFFFF',
                            border: '1px solid #E2E8F0',
                            borderRadius: '4px',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '2px',
                          }}
                        >
                          <div style={{ fontSize: '9.5px', color: '#64748B', fontWeight: 600, textTransform: 'uppercase' }}>
                            {d.dimension.replace('_', ' ')}
                          </div>
                          <div style={{ fontSize: '13px', fontWeight: 700, color: '#0F172A' }}>
                            {d.score !== null && d.score !== undefined ? `${d.score.toFixed(1)}` : '—'}
                            <span style={{ fontSize: '10px', color: '#64748B', fontWeight: 400 }}> ({Math.round(d.weight * 100)}%)</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Judge Summary Preview */}
                  {latestEval.summary && (
                    <div
                      style={{
                        marginTop: '10px',
                        padding: '8px 10px',
                        backgroundColor: '#FAF5FF',
                        border: '1px solid #E9D5FF',
                        borderRadius: '6px',
                        fontSize: '11.5px',
                        color: '#581C87',
                        lineHeight: 1.4,
                      }}
                    >
                      <strong>Judge Assessment: </strong>
                      {latestEval.summary}
                    </div>
                  )}
                </div>
              );
            })()}
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
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            {isActive ? (
              <>
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

                {orchState && orchState.state !== 'PAUSED' && !['COMPLETED', 'FAILED', 'CANCELLED'].includes(orchState.state) && (
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm"
                    onClick={handlePause}
                    disabled={pausing || orchState.pause_requested}
                    id="btn-pause-run-modal"
                    title="Pause execution safely at the next agent transition boundary"
                  >
                    <Pause size={13} color="#D97706" />
                    <span>{pausing || orchState.pause_requested ? 'Pausing...' : 'Pause at Boundary'}</span>
                  </button>
                )}

                {orchState && orchState.state === 'PAUSED' && (
                  <button
                    type="button"
                    className="btn btn-primary btn-sm"
                    onClick={handleResume}
                    disabled={resuming}
                    id="btn-resume-run-modal"
                    title="Resume paused autonomous execution"
                  >
                    <Play size={13} />
                    <span>{resuming ? 'Resuming...' : 'Resume Execution'}</span>
                  </button>
                )}
              </>
            ) : (
              <>
                <button
                  type="button"
                  className="btn btn-primary btn-sm"
                  onClick={handleStartAutonomous}
                  disabled={startingAutonomous || executingAgentTeam || executing}
                  id="btn-start-autonomous-modal"
                  style={{
                    backgroundColor: '#7C3AED',
                    borderColor: '#6D28D9',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px',
                  }}
                  title="Run autonomous multi-iteration engineering loop with automated Builder retries"
                >
                  <Sparkles size={13} />
                  <span>{startingAutonomous ? 'Starting Autonomous Loop...' : 'Run Autonomously'}</span>
                </button>

                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleStartAgentTeam}
                  disabled={executingAgentTeam || executing || startingAutonomous}
                  id="btn-start-agent-team-modal"
                  title="Run single-pass agent team (Architect → Builder → Tester → Breaker → Security)"
                >
                  <Bot size={13} />
                  <span>{executingAgentTeam ? 'Starting Agents...' : 'Run Agent Team (Manual)'}</span>
                </button>

                <button
                  type="button"
                  className="btn btn-secondary btn-sm"
                  onClick={handleStartRun}
                  disabled={executing || executingAgentTeam || startingAutonomous}
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
