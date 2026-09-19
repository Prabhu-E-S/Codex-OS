import React from 'react';
import {
  Award,
  CheckCircle2,
  AlertCircle,
  ArrowUpRight,
} from 'lucide-react';
import { ControlRoomEvaluation } from '../../api/types';

interface ControlRoomEvaluationProps {
  evaluation?: ControlRoomEvaluation | null;
  onOpenEvaluationsView?: () => void;
}

export const ControlRoomEvaluationPanel: React.FC<ControlRoomEvaluationProps> = ({
  evaluation,
  onOpenEvaluationsView,
}) => {
  if (!evaluation) {
    return (
      <div className="cr-empty-card">
        <Award size={24} className="text-muted" />
        <span className="empty-title">Evaluation Pending</span>
        <p className="empty-desc">
          Engineering evaluation and score calculation will become available once the autonomous run reaches a completion or terminal state.
        </p>
      </div>
    );
  }

  const score = evaluation.overall_score;
  const statusLabel = evaluation.status_label;

  const getStatusColorClass = (status: string) => {
    switch (status) {
      case 'STRONG':
        return 'status-strong';
      case 'ADEQUATE':
        return 'status-adequate';
      case 'WEAK':
        return 'status-weak';
      default:
        return 'status-insufficient';
    }
  };

  return (
    <div className="cr-evaluation-container">
      {/* Top Hero Banner */}
      <div className="cr-eval-hero">
        <div className="cr-eval-score-badge">
          <div className="score-num">
            {score !== null && score !== undefined ? score.toFixed(1) : '—'}
          </div>
          <div className="score-denom">/ 100</div>
        </div>

        <div className="cr-eval-hero-info">
          <div className="cr-eval-tag-row">
            <span className={`cr-eval-status-pill ${getStatusColorClass(statusLabel)}`}>
              {statusLabel}
            </span>
            <span className="cr-eval-version-pill">Score Engine {evaluation.score_version}</span>
          </div>

          <p className="cr-eval-summary-text">
            {evaluation.summary || 'Deterministic Engineering Score across 6 weighted dimensions.'}
          </p>

          {evaluation.formula && (
            <div className="cr-eval-formula-box">
              <code>{evaluation.formula}</code>
            </div>
          )}
        </div>

        {onOpenEvaluationsView && (
          <button
            className="btn btn-secondary btn-sm cr-view-full-eval-btn"
            onClick={onOpenEvaluationsView}
          >
            <span>Full Evaluations Page</span>
            <ArrowUpRight size={13} />
          </button>
        )}
      </div>

      {/* 6 Dimensions Breakdown Grid */}
      <div className="cr-dimensions-grid">
        {evaluation.dimensions.map((dim) => {
          const dimScore = dim.score;
          const pct = dimScore !== null && dimScore !== undefined ? Math.min(100, Math.max(0, dimScore)) : 0;

          return (
            <div key={dim.dimension} className="cr-dim-card">
              <div className="dim-card-header">
                <span className="dim-name">{dim.dimension.replace('_', ' ')}</span>
                <span className={`dim-status-pill ${getStatusColorClass(dim.status)}`}>
                  {dim.status}
                </span>
              </div>

              <div className="dim-score-row">
                <span className="dim-score-val">
                  {dimScore !== null && dimScore !== undefined ? dimScore.toFixed(1) : '—'}
                </span>
                <span className="dim-weight">Weight: {(dim.weight * 100).toFixed(0)}%</span>
              </div>

              <div className="dim-progress-track">
                <div
                  className={`dim-progress-fill ${getStatusColorClass(dim.status)}`}
                  style={{ width: `${pct}%` }}
                />
              </div>

              {dim.explanation && <p className="dim-expl">{dim.explanation}</p>}
            </div>
          );
        })}
      </div>

      {/* Judge Synthesis Highlights */}
      {(evaluation.strengths.length > 0 || evaluation.weaknesses.length > 0) && (
        <div className="cr-judge-highlights-grid">
          {evaluation.strengths.length > 0 && (
            <div className="cr-highlight-card strengths-card">
              <div className="highlight-card-header">
                <CheckCircle2 size={14} className="text-success" />
                <span>Verified Strengths</span>
              </div>
              <ul className="highlight-list">
                {evaluation.strengths.map((str, idx) => (
                  <li key={idx}>{str}</li>
                ))}
              </ul>
            </div>
          )}

          {evaluation.weaknesses.length > 0 && (
            <div className="cr-highlight-card weaknesses-card">
              <div className="highlight-card-header">
                <AlertCircle size={14} className="text-amber" />
                <span>Identified Deficiencies</span>
              </div>
              <ul className="highlight-list">
                {evaluation.weaknesses.map((weak, idx) => (
                  <li key={idx}>{weak}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
