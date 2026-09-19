import React from 'react';
import { Bot, Box, CheckSquare, Camera, ArrowLeft } from 'lucide-react';
import { NavTab } from './Sidebar';

interface PlaceholderViewProps {
  tab: NavTab;
  onBackToOverview: () => void;
}

export const PlaceholderView: React.FC<PlaceholderViewProps> = ({ tab, onBackToOverview }) => {
  const configs: Record<
    Exclude<NavTab, 'overview' | 'control-room'>,
    { title: string; subtitle: string; icon: React.ReactNode; description: string; phase: string }
  > = {
    agents: {
      title: 'Autonomous Agents Engine',
      subtitle: 'Multi-agent orchestration and role assignments',
      icon: <Bot size={28} color="#2563EB" />,
      description:
        'Architect, Builder, Tester, Breaker, Security, and Judge agents will be orchestrated here in Phase 2. The foundation is configured and ready for agent loop wiring.',
      phase: 'Phase 2 Subsystem',
    },
    workspaces: {
      title: 'Isolated Workspaces & Sandboxes',
      subtitle: 'Execution sandbox environments and workspace isolation',
      icon: <Box size={28} color="#2563EB" />,
      description:
        'Docker container sandboxes and isolated engineering workspaces will be provisioned here. Worktree isolation and file mounting will activate in subsequent phases.',
      phase: 'Phase 2 Subsystem',
    },
    evaluations: {
      title: 'Automated Code Evaluations',
      subtitle: 'Benchmark scoring, test suite pass rates, and security auditing',
      icon: <CheckSquare size={28} color="#2563EB" />,
      description:
        'Engineering evaluation suites, diff verification, regression detectors, and quality scoring models belong to upcoming phases.',
      phase: 'Phase 2 Subsystem',
    },
    snapshots: {
      title: 'Codebase Snapshots & Rollback',
      subtitle: 'Deterministic sandbox state capture and artifact checkpoints',
      icon: <Camera size={28} color="#2563EB" />,
      description:
        'State snapshots of workspaces before and after breaker/builder agent cycles will be tracked here.',
      phase: 'Phase 2 Subsystem',
    },
  };

  if (tab === 'overview' || tab === 'control-room') return null;
  const config = configs[tab];

  return (
    <div style={{ maxWidth: '780px' }}>
      <div style={{ marginBottom: '16px' }}>
        <button
          className="btn btn-secondary btn-sm"
          onClick={onBackToOverview}
          style={{ gap: '4px' }}
        >
          <ArrowLeft size={13} />
          <span>Back to Overview</span>
        </button>
      </div>

      <div className="card-panel">
        <div className="card-header">
          <div className="card-title">
            <span>{config.title}</span>
          </div>
          <span className="badge badge-muted">{config.phase}</span>
        </div>

        <div className="empty-state" style={{ padding: '48px 24px' }}>
          <div className="empty-icon" style={{ width: '56px', height: '56px' }}>
            {config.icon}
          </div>
          <div className="empty-title" style={{ fontSize: '16px' }}>
            {config.subtitle}
          </div>
          <div className="empty-desc" style={{ maxWidth: '460px', marginTop: '4px' }}>
            {config.description}
          </div>
          <div
            style={{
              marginTop: '16px',
              padding: '8px 14px',
              backgroundColor: 'var(--bg-subtle)',
              border: '1px solid var(--border-color)',
              borderRadius: '4px',
              fontSize: '11.5px',
              fontFamily: 'var(--font-mono)',
              color: 'var(--text-secondary)',
            }}
          >
            STATUS: Out of Scope for Phase 1 • Foundation Ready
          </div>
        </div>
      </div>
    </div>
  );
};
