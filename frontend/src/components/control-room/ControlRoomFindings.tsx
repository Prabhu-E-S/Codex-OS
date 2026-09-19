import React, { useState } from 'react';
import {
  Zap,
  Lock,
  ChevronDown,
  ChevronRight,
  FileCode,
  CheckCircle2,
  Terminal,
  Wrench,
} from 'lucide-react';
import { ControlRoomFinding, ControlRoomFindingsSummary } from '../../api/types';

interface ControlRoomFindingsProps {
  findings: ControlRoomFinding[];
  summary: ControlRoomFindingsSummary;
}

export const ControlRoomFindings: React.FC<ControlRoomFindingsProps> = ({ findings, summary }) => {
  const [typeFilter, setTypeFilter] = useState<'ALL' | 'BREAKER' | 'SECURITY'>('ALL');
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'OPEN' | 'RESOLVED'>('ALL');
  const [expandedId, setExpandedId] = useState<number | null>(null);

  const filteredFindings = findings.filter((f) => {
    if (typeFilter !== 'ALL' && f.type.toUpperCase() !== typeFilter) return false;
    if (severityFilter !== 'ALL' && f.severity.toUpperCase() !== severityFilter) return false;
    if (statusFilter === 'OPEN' && f.status === 'RESOLVED') return false;
    if (statusFilter === 'RESOLVED' && f.status !== 'RESOLVED') return false;
    return true;
  });

  const toggleExpand = (id: number) => {
    setExpandedId((prev) => (prev === id ? null : id));
  };

  return (
    <div className="cr-findings-container">
      {/* Findings Metrics Summary Banner */}
      <div className="cr-findings-metrics-banner">
        <div className="metric-box">
          <span className="metric-label">Total Findings</span>
          <span className="metric-value">{summary.total}</span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Critical</span>
          <span className="metric-value text-error">
            {summary.by_severity['CRITICAL'] || 0}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">High</span>
          <span className="metric-value text-amber">
            {summary.by_severity['HIGH'] || 0}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Medium</span>
          <span className="metric-value">
            {summary.by_severity['MEDIUM'] || 0}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Open Issues</span>
          <span className="metric-value">
            {summary.open}
          </span>
        </div>
        <div className="metric-box">
          <span className="metric-label">Resolved</span>
          <span className="metric-value text-success">
            {summary.resolved}
          </span>
        </div>
      </div>

      {/* Filter Toolbar */}
      <div className="cr-findings-toolbar">
        <div className="filter-group">
          <span className="filter-group-label">Type:</span>
          {(['ALL', 'BREAKER', 'SECURITY'] as const).map((t) => (
            <button
              key={t}
              className={`btn-pill ${typeFilter === t ? 'active' : ''}`}
              onClick={() => setTypeFilter(t)}
            >
              {t}
            </button>
          ))}
        </div>

        <div className="filter-group">
          <span className="filter-group-label">Severity:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'].map((s) => (
            <button
              key={s}
              className={`btn-pill ${severityFilter === s ? 'active' : ''}`}
              onClick={() => setSeverityFilter(s)}
            >
              {s}
            </button>
          ))}
        </div>

        <div className="filter-group">
          <span className="filter-group-label">Status:</span>
          {(['ALL', 'OPEN', 'RESOLVED'] as const).map((st) => (
            <button
              key={st}
              className={`btn-pill ${statusFilter === st ? 'active' : ''}`}
              onClick={() => setStatusFilter(st)}
            >
              {st}
            </button>
          ))}
        </div>
      </div>

      {/* Findings List */}
      <div className="cr-findings-list">
        {filteredFindings.length === 0 ? (
          <div className="cr-empty-card">
            <CheckCircle2 size={20} className="text-success" />
            <span>No findings match the selected filters.</span>
          </div>
        ) : (
          filteredFindings.map((f) => {
            const isExpanded = expandedId === f.id;
            const isCriticalOrHigh = f.severity === 'CRITICAL' || f.severity === 'HIGH';

            return (
              <div
                key={f.id}
                className={`cr-finding-card ${isCriticalOrHigh ? 'border-warning' : ''}`}
              >
                <div
                  className="cr-finding-header"
                  onClick={() => toggleExpand(f.id)}
                  role="button"
                  tabIndex={0}
                >
                  <div className="cr-finding-header-left">
                    <span className={`badge-severity sev-${f.severity.toLowerCase()}`}>
                      {f.severity}
                    </span>
                    <span className="badge-type">
                      {f.type === 'SECURITY' ? <Lock size={11} /> : <Zap size={11} />}
                      {f.type}
                    </span>
                    <span className="badge-iter">Iter {f.iteration}</span>
                    <span className="cr-finding-title">{f.title}</span>
                  </div>

                  <div className="cr-finding-header-right">
                    {f.file_path && (
                      <span className="cr-finding-loc">
                        <FileCode size={12} />
                        {f.file_path}:{f.line_number ?? ''}
                      </span>
                    )}
                    {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                  </div>
                </div>

                {isExpanded && (
                  <div className="cr-finding-details">
                    <p className="cr-finding-desc">{f.description}</p>

                    {f.evidence && (
                      <div className="detail-section">
                        <span className="detail-label">
                          <Terminal size={12} /> Verified Evidence Snippet
                        </span>
                        <pre className="cr-code-snippet">
                          <code>{f.evidence}</code>
                        </pre>
                      </div>
                    )}

                    {f.reproduction && (
                      <div className="detail-section">
                        <span className="detail-label">
                          <Terminal size={12} /> Reproduction Command / Payload
                        </span>
                        <pre className="cr-code-snippet">
                          <code>{f.reproduction}</code>
                        </pre>
                      </div>
                    )}

                    {f.remediation && (
                      <div className="detail-section">
                        <span className="detail-label">
                          <Wrench size={12} /> Recommended Remediation
                        </span>
                        <p className="cr-remediation-text">{f.remediation}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
