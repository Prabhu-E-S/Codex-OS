import React, { useState } from 'react';
import {
  Pause,
  Play,
  StopCircle,
  Award,
  AlertTriangle,
  Eye,
} from 'lucide-react';
import { ControlRoomRun, ControlRoomOrchestration, ControlRoomEvaluation } from '../../api/types';
import { api } from '../../api/client';

interface RunControlsProps {
  run: ControlRoomRun;
  orchestration?: ControlRoomOrchestration | null;
  evaluation?: ControlRoomEvaluation | null;
  onRunUpdated: () => void;
  onOpenEvaluationsView?: () => void;
}

export const RunControls: React.FC<RunControlsProps> = ({
  run,
  orchestration,
  evaluation,
  onRunUpdated,
  onOpenEvaluationsView,
}) => {
  const [showCancelModal, setShowCancelModal] = useState(false);
  const [pausing, setPausing] = useState(false);
  const [resuming, setResuming] = useState(false);
  const [cancelling, setCancelling] = useState(false);
  const [evaluating, setEvaluating] = useState(false);

  const status = run.status;
  const orchState = orchestration?.state;

  const isRunning = status === 'RUNNING' || status === 'STARTING' || (orchestration?.is_active ?? false);
  const isPaused = orchState === 'PAUSED' || status === 'PAUSED';
  const isCompleted = status === 'COMPLETED' || orchState === 'COMPLETED';
  const isFailed = status === 'FAILED' || orchState === 'FAILED';
  const isCancelled = status === 'CANCELLED' || orchState === 'CANCELLED';

  // Pause handler
  const handlePause = async () => {
    setPausing(true);
    try {
      await api.pauseRun(run.id);
      onRunUpdated();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to request pause');
    } finally {
      setPausing(false);
    }
  };

  // Resume handler
  const handleResume = async () => {
    setResuming(true);
    try {
      await api.resumeRun(run.id);
      onRunUpdated();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to resume run');
    } finally {
      setResuming(false);
    }
  };

  // Cancel handler (destructive)
  const handleConfirmCancel = async () => {
    setCancelling(true);
    try {
      if (run.mode === 'AUTONOMOUS' || orchestration) {
        await api.cancelAutonomousRun(run.id);
      } else {
        await api.cancelRun(run.id);
      }
      setShowCancelModal(false);
      onRunUpdated();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to cancel run');
    } finally {
      setCancelling(false);
    }
  };

  // Evaluate handler
  const handleEvaluate = async () => {
    setEvaluating(true);
    try {
      await api.evaluateRun(run.id);
      onRunUpdated();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to evaluate run');
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="cr-run-controls-bar">
      <div className="cr-controls-label">
        <span>RUN CONTROLS</span>
      </div>

      <div className="cr-controls-buttons">
        {/* Active running controls */}
        {isRunning && !isPaused && (
          <>
            <button
              className="btn btn-warning btn-sm"
              onClick={handlePause}
              disabled={pausing || orchestration?.pause_requested}
              title="Pause at the next agent transition boundary"
            >
              <Pause size={13} />
              <span>{orchestration?.pause_requested ? 'Pause Requested...' : 'Pause at Boundary'}</span>
            </button>

            <button
              className="btn btn-danger btn-sm"
              onClick={() => setShowCancelModal(true)}
              disabled={cancelling}
              title="Cancel run and stop active sandboxes"
            >
              <StopCircle size={13} />
              <span>Cancel Run</span>
            </button>
          </>
        )}

        {/* Paused state controls */}
        {isPaused && (
          <>
            <button
              className="btn btn-primary btn-sm"
              onClick={handleResume}
              disabled={resuming}
              title="Resume execution from paused boundary"
            >
              <Play size={13} />
              <span>Resume Execution</span>
            </button>

            <button
              className="btn btn-danger btn-sm"
              onClick={() => setShowCancelModal(true)}
              disabled={cancelling}
            >
              <StopCircle size={13} />
              <span>Cancel Run</span>
            </button>
          </>
        )}

        {/* Completed / Failed state controls */}
        {(isCompleted || isFailed) && (
          <>
            {!evaluation ? (
              <button
                className="btn btn-primary btn-sm"
                onClick={handleEvaluate}
                disabled={evaluating}
                title="Calculate Engineering Score across all 6 dimensions"
              >
                <Award size={13} />
                <span>{evaluating ? 'Evaluating...' : 'Evaluate Run'}</span>
              </button>
            ) : (
              <button
                className="btn btn-secondary btn-sm"
                onClick={onOpenEvaluationsView}
                title="Inspect detailed evaluation evidence"
              >
                <Eye size={13} />
                <span>View Evaluation ({evaluation.overall_score?.toFixed(1) ?? '—'}/100)</span>
              </button>
            )}
          </>
        )}

        {isCancelled && (
          <span className="text-muted font-mono" style={{ fontSize: '12px' }}>
            Run cancelled. Execution terminated.
          </span>
        )}
      </div>

      {/* Confirmation Modal for Destructive Cancellation */}
      {showCancelModal && (
        <div className="cr-confirm-modal-backdrop">
          <div className="cr-confirm-modal">
            <div className="cr-confirm-header">
              <AlertTriangle size={18} className="text-error" />
              <h4>Cancel Engineering Run?</h4>
            </div>

            <p className="cr-confirm-body">
              This will immediately stop future agent execution steps and attempt to terminate active
              Docker sandbox container processes for Run #{run.id}.
            </p>

            <div className="cr-confirm-actions">
              <button
                className="btn btn-secondary btn-sm"
                onClick={() => setShowCancelModal(false)}
                disabled={cancelling}
              >
                Keep Running
              </button>
              <button
                className="btn btn-danger btn-sm"
                onClick={handleConfirmCancel}
                disabled={cancelling}
              >
                {cancelling ? 'Cancelling...' : 'Cancel Run'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
