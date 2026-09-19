import React, { useState, useEffect } from 'react';
import {
  Activity,
  Terminal,
  Award,
  AlertTriangle,
  FolderGit2,
  Clock,
  ChevronDown,
  RefreshCw,
  Plus,
} from 'lucide-react';
import { Project, EngineeringRun, ControlRoomAgent } from '../api/types';
import { useRunControlRoom } from '../hooks/useRunControlRoom';
import { ControlRoomHeader } from '../components/control-room/ControlRoomHeader';
import { CurrentStatePanel } from '../components/control-room/CurrentStatePanel';
import { AgentPipeline } from '../components/control-room/AgentPipeline';
import { AgentGraph } from '../components/control-room/AgentGraph';
import { AgentDetailDrawer } from '../components/control-room/AgentDetailDrawer';
import { IterationTimeline } from '../components/control-room/IterationTimeline';
import { OrchestrationEventsTimeline } from '../components/control-room/OrchestrationEventsTimeline';
import { ControlRoomFindings } from '../components/control-room/ControlRoomFindings';
import { ControlRoomEvaluationPanel } from '../components/control-room/ControlRoomEvaluation';
import { ControlRoomWorkspacesSandboxes } from '../components/control-room/ControlRoomWorkspacesSandboxes';
import { ControlRoomLogsViewer } from '../components/control-room/ControlRoomLogsViewer';
import { RunControls } from '../components/control-room/RunControls';

interface ControlRoomViewProps {
  currentProject: Project | null;
  runs: EngineeringRun[];
  selectedRunId: number | null;
  onSelectRunId: (runId: number) => void;
  onOpenEvaluationsView?: () => void;
  onOpenCreateRun?: () => void;
}

type BottomTab = 'findings' | 'evaluation' | 'environments' | 'logs' | 'events';

export const ControlRoomView: React.FC<ControlRoomViewProps> = ({
  currentProject,
  runs,
  selectedRunId,
  onSelectRunId,
  onOpenEvaluationsView,
  onOpenCreateRun,
}) => {
  // If no run selected, choose the latest active or newest run
  const activeRunId = selectedRunId ?? (runs.length > 0 ? runs[0].id : null);

  const { snapshot, loading, error, isPolling, lastUpdated, isStale, refresh } =
    useRunControlRoom(activeRunId);

  const [activeBottomTab, setActiveBottomTab] = useState<BottomTab>('findings');
  const [selectedAgentForDrawer, setSelectedAgentForDrawer] = useState<ControlRoomAgent | null>(null);

  // Auto-switch bottom tab if evaluation becomes available and user hasn't toggled yet
  useEffect(() => {
    if (snapshot?.evaluation && activeBottomTab === 'findings' && snapshot.findings.length === 0) {
      setActiveBottomTab('evaluation');
    }
  }, [snapshot?.evaluation, activeBottomTab, snapshot?.findings.length]);

  if (!currentProject) {
    return (
      <div className="cr-empty-container">
        <Activity size={32} className="text-muted" />
        <h2>No Project Selected</h2>
        <p>Select or create a project from the top bar to inspect its Control Room.</p>
      </div>
    );
  }

  if (runs.length === 0) {
    return (
      <div className="cr-empty-container">
        <Activity size={32} className="text-muted" />
        <h2>No Engineering Runs</h2>
        <p>Create an engineering run to observe agent execution, iteration loops, and findings.</p>
        {onOpenCreateRun && (
          <button className="btn btn-primary btn-sm" onClick={onOpenCreateRun}>
            <Plus size={14} />
            <span>Create Engineering Run</span>
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="cr-page-layout">
      {/* Top Run Selector Bar */}
      <div className="cr-run-selector-bar">
        <div className="cr-selector-left">
          <span className="cr-selector-label">ENGINEERING RUN:</span>
          <div className="cr-select-wrapper">
            <select
              className="cr-run-select"
              value={activeRunId ?? ''}
              onChange={(e) => onSelectRunId(Number(e.target.value))}
            >
              {runs.map((r) => (
                <option key={r.id} value={r.id}>
                  Run #{r.id} &bull; {r.status} &bull; {r.goal.slice(0, 45)}
                  {r.goal.length > 45 ? '...' : ''}
                </option>
              ))}
            </select>
            <ChevronDown size={14} className="select-caret" />
          </div>
        </div>

        <div className="cr-selector-right">
          <span className="cr-total-runs-tag">{runs.length} runs in {currentProject.name}</span>
          {onOpenCreateRun && (
            <button className="btn btn-secondary btn-xs" onClick={onOpenCreateRun}>
              <Plus size={12} />
              <span>New Run</span>
            </button>
          )}
        </div>
      </div>

      {loading && !snapshot ? (
        <div className="cr-loading-state">
          <RefreshCw size={24} className="spin-icon text-muted" />
          <span>Connecting to Control Room snapshot...</span>
        </div>
      ) : error && !snapshot ? (
        <div className="cr-error-state">
          <AlertTriangle size={24} className="text-error" />
          <h3>Failed to Load Control Room</h3>
          <p>{error}</p>
          <button className="btn btn-secondary btn-sm" onClick={refresh}>
            <RefreshCw size={13} />
            <span>Try Again</span>
          </button>
        </div>
      ) : snapshot ? (
        <>
          {/* Header */}
          <ControlRoomHeader
            run={snapshot.run}
            orchestration={snapshot.orchestration}
            isPolling={isPolling}
            isStale={isStale}
            lastUpdated={lastUpdated}
            onRefresh={refresh}
            refreshing={loading}
          />

          {/* Run Action Controls */}
          <RunControls
            run={snapshot.run}
            orchestration={snapshot.orchestration}
            evaluation={snapshot.evaluation}
            onRunUpdated={refresh}
            onOpenEvaluationsView={onOpenEvaluationsView}
          />

          {/* Current State Panel */}
          <CurrentStatePanel
            run={snapshot.run}
            orchestration={snapshot.orchestration}
          />

          {/* Linear Pipeline */}
          <AgentPipeline
            agents={snapshot.agents}
            activeAgentName={snapshot.orchestration?.current_agent}
            currentIteration={snapshot.run.iteration}
            evaluation={snapshot.evaluation}
            onSelectAgent={(agent) => setSelectedAgentForDrawer(agent)}
            onSelectEvaluation={() => setActiveBottomTab('evaluation')}
          />

          {/* Middle Row: Graph + Iterations */}
          <div className="cr-middle-grid">
            <AgentGraph
              agents={snapshot.agents}
              orchestration={snapshot.orchestration}
              evaluation={snapshot.evaluation}
              onSelectAgent={(agent) => setSelectedAgentForDrawer(agent)}
              onSelectEvaluation={() => setActiveBottomTab('evaluation')}
            />

            <IterationTimeline
              iterations={snapshot.iterations}
              currentIteration={snapshot.run.iteration}
            />
          </div>

          {/* Bottom Tabs & Panels */}
          <div className="cr-bottom-section">
            <div className="cr-tab-nav">
              <button
                className={`cr-tab-btn ${activeBottomTab === 'findings' ? 'active' : ''}`}
                onClick={() => setActiveBottomTab('findings')}
              >
                <AlertTriangle size={14} />
                <span>Findings</span>
                {snapshot.findings_summary.total > 0 && (
                  <span className="tab-counter">{snapshot.findings_summary.total}</span>
                )}
              </button>

              <button
                className={`cr-tab-btn ${activeBottomTab === 'evaluation' ? 'active' : ''}`}
                onClick={() => setActiveBottomTab('evaluation')}
              >
                <Award size={14} />
                <span>Evaluation</span>
                {snapshot.evaluation?.overall_score !== undefined &&
                  snapshot.evaluation.overall_score !== null && (
                    <span className="tab-counter">
                      {snapshot.evaluation.overall_score.toFixed(0)}
                    </span>
                  )}
              </button>

              <button
                className={`cr-tab-btn ${activeBottomTab === 'environments' ? 'active' : ''}`}
                onClick={() => setActiveBottomTab('environments')}
              >
                <FolderGit2 size={14} />
                <span>Workspaces & Sandboxes</span>
                <span className="tab-counter">
                  {snapshot.workspaces.length + snapshot.sandboxes.length}
                </span>
              </button>

              <button
                className={`cr-tab-btn ${activeBottomTab === 'logs' ? 'active' : ''}`}
                onClick={() => setActiveBottomTab('logs')}
              >
                <Terminal size={14} />
                <span>Execution Logs</span>
                {snapshot.logs.total_lines > 0 && (
                  <span className="tab-counter">{snapshot.logs.total_lines}</span>
                )}
              </button>

              <button
                className={`cr-tab-btn ${activeBottomTab === 'events' ? 'active' : ''}`}
                onClick={() => setActiveBottomTab('events')}
              >
                <Clock size={14} />
                <span>Timeline Events</span>
                {snapshot.recent_events.length > 0 && (
                  <span className="tab-counter">{snapshot.recent_events.length}</span>
                )}
              </button>
            </div>

            <div className="cr-tab-panel-container">
              {activeBottomTab === 'findings' && (
                <ControlRoomFindings
                  findings={snapshot.findings}
                  summary={snapshot.findings_summary}
                />
              )}

              {activeBottomTab === 'evaluation' && (
                <ControlRoomEvaluationPanel
                  evaluation={snapshot.evaluation}
                  onOpenEvaluationsView={onOpenEvaluationsView}
                />
              )}

              {activeBottomTab === 'environments' && (
                <ControlRoomWorkspacesSandboxes
                  workspaces={snapshot.workspaces}
                  sandboxes={snapshot.sandboxes}
                />
              )}

              {activeBottomTab === 'logs' && (
                <ControlRoomLogsViewer
                  logs={snapshot.logs}
                  isRunning={snapshot.run.status === 'RUNNING' || snapshot.run.status === 'STARTING'}
                />
              )}

              {activeBottomTab === 'events' && (
                <OrchestrationEventsTimeline events={snapshot.recent_events} />
              )}
            </div>
          </div>

          {/* Slide-over Agent Detail Drawer */}
          <AgentDetailDrawer
            agent={selectedAgentForDrawer}
            onClose={() => setSelectedAgentForDrawer(null)}
          />
        </>
      ) : null}
    </div>
  );
};
