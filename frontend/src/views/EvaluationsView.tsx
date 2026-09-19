import React, { useState, useEffect, useCallback } from 'react';
import {
  RefreshCw,
  Award,
  ChevronDown,
  ChevronRight,
  ShieldCheck,
  CheckCircle2,
  AlertTriangle,
  Info,
  Clock,
  ExternalLink,
} from 'lucide-react';
import {
  Project,
  Evaluation,
  EvaluationDimension,
  EvaluationEvidence,
  DimensionStatus,
} from '../api/types';
import { api } from '../api/client';

interface EvaluationsViewProps {
  currentProject: Project | null;
  onSelectRun?: (runId: number) => void;
}

export const EvaluationsView: React.FC<EvaluationsViewProps> = ({
  currentProject,
  onSelectRun,
}) => {
  const [evaluations, setEvaluations] = useState<Evaluation[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedEvalId, setSelectedEvalId] = useState<number | null>(null);
  const [selectedEval, setSelectedEval] = useState<Evaluation | null>(null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [expandedDim, setExpandedDim] = useState<string | null>(null);
  const [reEvaluating, setReEvaluating] = useState(false);

  const fetchProjectEvaluations = useCallback(async () => {
    if (!currentProject) return;
    setLoading(true);
    try {
      const data = await api.getProjectEvaluations(currentProject.id);
      setEvaluations(data);
      if (data.length > 0 && (!selectedEvalId || !data.some((e) => e.id === selectedEvalId))) {
        setSelectedEvalId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load project evaluations:', err);
      setEvaluations([]);
    } finally {
      setLoading(false);
    }
  }, [currentProject, selectedEvalId]);

  const fetchEvaluationDetail = useCallback(async (evalId: number) => {
    setLoadingDetail(true);
    try {
      const detail = await api.getEvaluation(evalId);
      setSelectedEval(detail);
    } catch (err) {
      console.error('Failed to fetch evaluation details:', err);
    } finally {
      setLoadingDetail(false);
    }
  }, []);

  useEffect(() => {
    fetchProjectEvaluations();
  }, [fetchProjectEvaluations]);

  useEffect(() => {
    if (selectedEvalId) {
      fetchEvaluationDetail(selectedEvalId);
    } else {
      setSelectedEval(null);
    }
  }, [selectedEvalId, fetchEvaluationDetail]);

  const handleReEvaluate = async (runId: number) => {
    setReEvaluating(true);
    try {
      const newEval = await api.evaluateRun(runId);
      await fetchProjectEvaluations();
      setSelectedEvalId(newEval.id);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to trigger re-evaluation');
    } finally {
      setReEvaluating(false);
    }
  };

  const getStatusBadge = (status: DimensionStatus | string) => {
    switch (status) {
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

  if (!currentProject) {
    return (
      <div className="view-container">
        <div className="empty-state" style={{ padding: '48px' }}>
          <div className="empty-desc">Select or create a project to view evaluations.</div>
        </div>
      </div>
    );
  }

  return (
    <div className="view-container" style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
      {/* Header Banner */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '14px 18px',
          backgroundColor: '#FFFFFF',
          borderRadius: '8px',
          border: '1px solid #E2E8F0',
          boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '34px',
              height: '34px',
              borderRadius: '6px',
              backgroundColor: '#EFF6FF',
              color: '#2563EB',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: '1px solid #DBEAFE',
            }}
          >
            <Award size={18} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 style={{ fontSize: '15px', fontWeight: 700, margin: 0, color: '#0F172A' }}>
                Engineering Evaluation & Score
              </h2>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 600,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  backgroundColor: '#F3E8FF',
                  color: '#7C3AED',
                  border: '1px solid #E9D5FF',
                }}
              >
                Phase 8
              </span>
            </div>
            <div style={{ fontSize: '11.5px', color: '#64748B', marginTop: '2px' }}>
              Evidence-backed, deterministic assessment across Correctness, Coverage, Security, Maintainability, Performance, and Regression Risk.
            </div>
          </div>
        </div>

        <button
          className="btn btn-secondary btn-sm"
          onClick={fetchProjectEvaluations}
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={12} className={loading ? 'spinning' : ''} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Main Split Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 380px) 1fr', gap: '16px', alignItems: 'start' }}>
        {/* Left Column: Evaluation List */}
        <div
          style={{
            backgroundColor: '#FFFFFF',
            borderRadius: '8px',
            border: '1px solid #E2E8F0',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              padding: '12px 14px',
              borderBottom: '1px solid #E2E8F0',
              fontWeight: 600,
              fontSize: '12.5px',
              color: '#0F172A',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span>Project Evaluations ({evaluations.length})</span>
          </div>

          {evaluations.length === 0 ? (
            <div style={{ padding: '24px', textAlign: 'center', color: '#64748B', fontSize: '12px' }}>
              {loading ? 'Loading evaluations...' : 'No evaluations found. Open a completed run to trigger evaluation.'}
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {evaluations.map((ev) => {
                const isSelected = selectedEvalId === ev.id;
                const statusStyle = getStatusBadge(ev.status_label);

                return (
                  <div
                    key={ev.id}
                    onClick={() => setSelectedEvalId(ev.id)}
                    style={{
                      padding: '12px 14px',
                      borderBottom: '1px solid #F1F5F9',
                      cursor: 'pointer',
                      backgroundColor: isSelected ? '#F8FAFC' : '#FFFFFF',
                      borderLeft: isSelected ? '3px solid #2563EB' : '3px solid transparent',
                      transition: 'background-color 0.15s ease',
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '6px' }}>
                      <span style={{ fontSize: '11px', fontWeight: 600, color: '#2563EB' }}>
                        Run #{ev.engineering_run_id}
                      </span>
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
                    </div>

                    <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginBottom: '6px' }}>
                      <span style={{ fontSize: '20px', fontWeight: 800, color: '#0F172A' }}>
                        {ev.overall_score !== null && ev.overall_score !== undefined
                          ? ev.overall_score.toFixed(1)
                          : '—'}
                      </span>
                      <span style={{ fontSize: '12px', color: '#64748B', fontWeight: 500 }}>/ 100</span>
                      <span style={{ fontSize: '10px', color: '#94A3B8', marginLeft: 'auto' }}>
                        {ev.score_version}
                      </span>
                    </div>

                    <div style={{ fontSize: '11px', color: '#64748B', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={11} />
                      <span>{new Date(ev.created_at).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right Column: Detailed Evaluation Inspector */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {selectedEval ? (
            <>
              {/* Overall Score Banner Card */}
              <div
                style={{
                  backgroundColor: '#FFFFFF',
                  borderRadius: '8px',
                  border: '1px solid #E2E8F0',
                  padding: '18px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  gap: '16px',
                }}
              >
                <div>
                  <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                    ENGINEERING SCORE
                  </div>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: '10px', marginTop: '4px' }}>
                    <span style={{ fontSize: '32px', fontWeight: 800, color: '#0F172A', lineHeight: 1 }}>
                      {selectedEval.overall_score !== null && selectedEval.overall_score !== undefined
                        ? selectedEval.overall_score.toFixed(1)
                        : '—'}
                    </span>
                    <span style={{ fontSize: '16px', fontWeight: 600, color: '#64748B' }}>/ 100</span>
                    <span
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '9999px',
                        backgroundColor: getStatusBadge(selectedEval.status_label).bg,
                        color: getStatusBadge(selectedEval.status_label).color,
                        border: `1px solid ${getStatusBadge(selectedEval.status_label).border}`,
                      }}
                    >
                      {getStatusBadge(selectedEval.status_label).label}
                    </span>
                  </div>
                  <div style={{ fontSize: '11.5px', color: '#64748B', marginTop: '6px' }}>
                    Version {selectedEval.score_version} • Evaluated {new Date(selectedEval.created_at).toLocaleString()}
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                  {onSelectRun && (
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => onSelectRun(selectedEval.engineering_run_id)}
                      style={{ display: 'flex', alignItems: 'center', gap: '5px' }}
                    >
                      <ExternalLink size={12} />
                      <span>View Run #{selectedEval.engineering_run_id}</span>
                    </button>
                  )}
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={() => handleReEvaluate(selectedEval.engineering_run_id)}
                    disabled={reEvaluating}
                    style={{ display: 'flex', alignItems: 'center', gap: '5px' }}
                  >
                    <RefreshCw size={12} className={reEvaluating ? 'spinning' : ''} />
                    <span>{reEvaluating ? 'Evaluating...' : 'Re-evaluate'}</span>
                  </button>
                </div>
              </div>

              {/* Scoring Formula Card */}
              {selectedEval.formula && (
                <div
                  style={{
                    backgroundColor: '#F8FAFC',
                    borderRadius: '8px',
                    border: '1px solid #E2E8F0',
                    padding: '12px 16px',
                    fontSize: '12px',
                  }}
                >
                  <div style={{ fontWeight: 600, color: '#334155', marginBottom: '4px' }}>
                    Deterministic Calculation Formula:
                  </div>
                  <div
                    style={{
                      fontFamily: 'JetBrains Mono, monospace',
                      color: '#0F172A',
                      fontSize: '11.5px',
                      backgroundColor: '#FFFFFF',
                      padding: '8px 10px',
                      borderRadius: '4px',
                      border: '1px solid #CBD5E1',
                    }}
                  >
                    {selectedEval.formula}
                  </div>
                </div>
              )}

              {/* Dimension Breakdown Rows */}
              <div
                style={{
                  backgroundColor: '#FFFFFF',
                  borderRadius: '8px',
                  border: '1px solid #E2E8F0',
                  padding: '16px',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: '13px', color: '#0F172A', marginBottom: '12px' }}>
                  Evaluation Dimensions
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {selectedEval.dimensions?.map((dim: EvaluationDimension) => {
                    const isExpanded = expandedDim === dim.dimension;
                    const dimStyle = getStatusBadge(dim.status);
                    const evidenceForDim = selectedEval.evidence_items?.filter(
                      (e: EvaluationEvidence) => e.dimension === dim.dimension
                    ) || [];

                    return (
                      <div
                        key={dim.id}
                        style={{
                          border: '1px solid #E2E8F0',
                          borderRadius: '6px',
                          overflow: 'hidden',
                          backgroundColor: '#FFFFFF',
                        }}
                      >
                        <div
                          style={{
                            padding: '10px 14px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center',
                            backgroundColor: isExpanded ? '#F8FAFC' : '#FFFFFF',
                            cursor: 'pointer',
                          }}
                          onClick={() => setExpandedDim(isExpanded ? null : dim.dimension)}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            {isExpanded ? <ChevronDown size={14} color="#64748B" /> : <ChevronRight size={14} color="#64748B" />}
                            <span style={{ fontSize: '12.5px', fontWeight: 600, color: '#0F172A' }}>
                              {dim.dimension.replace('_', ' ')}
                            </span>
                            <span
                              style={{
                                fontSize: '10px',
                                fontWeight: 700,
                                padding: '1px 6px',
                                borderRadius: '4px',
                                backgroundColor: dimStyle.bg,
                                color: dimStyle.color,
                                border: `1px solid ${dimStyle.border}`,
                              }}
                            >
                              {dimStyle.label}
                            </span>
                            <span
                              style={{
                                fontSize: '10px',
                                padding: '1px 6px',
                                borderRadius: '4px',
                                backgroundColor: '#F1F5F9',
                                color: '#475569',
                                fontWeight: 500,
                              }}
                            >
                              Weight: {(dim.weight * 100).toFixed(0)}%
                            </span>
                          </div>

                          <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
                            <span style={{ fontSize: '16px', fontWeight: 700, color: '#0F172A' }}>
                              {dim.score !== null && dim.score !== undefined ? dim.score.toFixed(1) : '—'}
                            </span>
                            <span style={{ fontSize: '11px', color: '#64748B' }}>/ 100</span>
                          </div>
                        </div>

                        {/* Explanation snippet */}
                        <div style={{ padding: '0 14px 10px 36px', fontSize: '12px', color: '#475569', lineHeight: 1.4 }}>
                          {dim.explanation}
                          {dim.limitations && (
                            <div style={{ color: '#D97706', fontSize: '11px', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                              <Info size={12} />
                              <span>{dim.limitations}</span>
                            </div>
                          )}
                        </div>

                        {/* Expanded Evidence Drawer */}
                        {isExpanded && (
                          <div
                            style={{
                              borderTop: '1px solid #E2E8F0',
                              padding: '12px 16px',
                              backgroundColor: '#F8FAFC',
                            }}
                          >
                            <div style={{ fontSize: '11px', fontWeight: 600, color: '#334155', marginBottom: '8px', textTransform: 'uppercase' }}>
                              Supporting Evidence ({evidenceForDim.length} items)
                            </div>

                            {evidenceForDim.length === 0 ? (
                              <div style={{ fontSize: '11.5px', color: '#64748B' }}>
                                No raw evidence items captured for this dimension.
                              </div>
                            ) : (
                              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                {evidenceForDim.map((ev: EvaluationEvidence) => (
                                  <div
                                    key={ev.id}
                                    style={{
                                      backgroundColor: '#FFFFFF',
                                      border: '1px solid #CBD5E1',
                                      borderRadius: '4px',
                                      padding: '8px 10px',
                                      fontSize: '11.5px',
                                    }}
                                  >
                                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                                      <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                                        <span
                                          style={{
                                            fontSize: '9.5px',
                                            fontWeight: 700,
                                            padding: '1px 5px',
                                            borderRadius: '3px',
                                            backgroundColor: '#EFF6FF',
                                            color: '#2563EB',
                                            border: '1px solid #BFDBFE',
                                          }}
                                        >
                                          {ev.source_type}
                                        </span>
                                        <span style={{ fontWeight: 600, color: '#0F172A' }}>
                                          {ev.metric_name}
                                        </span>
                                        {ev.metric_value && (
                                          <span
                                            style={{
                                              fontFamily: 'JetBrains Mono, monospace',
                                              backgroundColor: '#F1F5F9',
                                              padding: '1px 4px',
                                              borderRadius: '3px',
                                              color: '#334155',
                                            }}
                                          >
                                            {ev.metric_value}
                                          </span>
                                        )}
                                      </div>
                                      {ev.file_path && (
                                        <span style={{ fontSize: '10px', color: '#64748B', fontFamily: 'JetBrains Mono, monospace' }}>
                                          {ev.file_path}{ev.line_number ? `:${ev.line_number}` : ''}
                                        </span>
                                      )}
                                    </div>

                                    <div style={{ color: '#475569', lineHeight: 1.4 }}>
                                      {ev.description}
                                    </div>

                                    {ev.evidence_text && (
                                      <div
                                        style={{
                                          marginTop: '6px',
                                          padding: '6px 8px',
                                          backgroundColor: '#0F172A',
                                          color: '#F8FAFC',
                                          fontFamily: 'JetBrains Mono, monospace',
                                          fontSize: '10.5px',
                                          borderRadius: '3px',
                                          whiteSpace: 'pre-wrap',
                                          lineHeight: 1.4,
                                        }}
                                      >
                                        {ev.evidence_text}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Judge Qualitative Synthesis Panel */}
              <div
                style={{
                  backgroundColor: '#FFFFFF',
                  borderRadius: '8px',
                  border: '1px solid #E2E8F0',
                  padding: '16px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px' }}>
                  <ShieldCheck size={16} color="#7C3AED" />
                  <span style={{ fontWeight: 600, fontSize: '13px', color: '#0F172A' }}>
                    Judge Agent Qualitative Assessment
                  </span>
                  <span
                    style={{
                      fontSize: '10px',
                      fontWeight: 600,
                      padding: '1px 6px',
                      borderRadius: '4px',
                      backgroundColor: '#F5F3FF',
                      color: '#7C3AED',
                      border: '1px solid #DDD6FE',
                    }}
                  >
                    Evidence Synthesis
                  </span>
                </div>

                {selectedEval.summary && (
                  <div
                    style={{
                      padding: '10px 12px',
                      backgroundColor: '#F8FAFC',
                      border: '1px solid #E2E8F0',
                      borderRadius: '6px',
                      fontSize: '12px',
                      color: '#334155',
                      lineHeight: 1.5,
                      marginBottom: '12px',
                    }}
                  >
                    <strong>Executive Summary: </strong>
                    {selectedEval.summary}
                  </div>
                )}

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  {/* Strengths */}
                  <div style={{ border: '1px solid #E2E8F0', borderRadius: '6px', padding: '10px 12px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: '#059669', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <CheckCircle2 size={13} />
                      <span>Verified Strengths</span>
                    </div>
                    {selectedEval.strengths.length === 0 ? (
                      <div style={{ fontSize: '11.5px', color: '#94A3B8' }}>None identified.</div>
                    ) : (
                      <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '11.5px', color: '#334155', lineHeight: 1.4 }}>
                        {selectedEval.strengths.map((s: string, idx: number) => (
                          <li key={idx} style={{ marginBottom: '4px' }}>{s}</li>
                        ))}
                      </ul>
                    )}
                  </div>

                  {/* Weaknesses */}
                  <div style={{ border: '1px solid #E2E8F0', borderRadius: '6px', padding: '10px 12px' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: '#DC2626', marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <AlertTriangle size={13} />
                      <span>Verified Weaknesses</span>
                    </div>
                    {selectedEval.weaknesses.length === 0 ? (
                      <div style={{ fontSize: '11.5px', color: '#94A3B8' }}>None identified.</div>
                    ) : (
                      <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '11.5px', color: '#334155', lineHeight: 1.4 }}>
                        {selectedEval.weaknesses.map((w: string, idx: number) => (
                          <li key={idx} style={{ marginBottom: '4px' }}>{w}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                </div>

                {/* Limitations */}
                {selectedEval.limitations.length > 0 && (
                  <div style={{ marginTop: '12px', border: '1px solid #E2E8F0', borderRadius: '6px', padding: '10px 12px', backgroundColor: '#FAFAFA' }}>
                    <div style={{ fontSize: '11px', fontWeight: 700, color: '#64748B', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Info size={13} />
                      <span>Evaluation Limitations & Gaps</span>
                    </div>
                    <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '11.5px', color: '#64748B', lineHeight: 1.4 }}>
                      {selectedEval.limitations.map((l: string, idx: number) => (
                        <li key={idx} style={{ marginBottom: '4px' }}>{l}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div
              style={{
                backgroundColor: '#FFFFFF',
                borderRadius: '8px',
                border: '1px solid #E2E8F0',
                padding: '48px',
                textAlign: 'center',
                color: '#64748B',
                fontSize: '12.5px',
              }}
            >
              {loadingDetail ? 'Loading evaluation details...' : 'Select an evaluation on the left to inspect scores, dimensions, and evidence.'}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
