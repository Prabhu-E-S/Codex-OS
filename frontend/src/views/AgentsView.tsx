import React from 'react';
import {
  Compass,
  Hammer,
  CheckCheck,
  Shield,
  ArrowRight,
  FolderGit2,
  Box,
  Plus,
} from 'lucide-react';
import { Project } from '../api/types';

interface AgentsViewProps {
  currentProject: Project | null;
  onOpenCreateRun?: () => void;
}

export const AgentsView: React.FC<AgentsViewProps> = ({
  currentProject,
  onOpenCreateRun,
}) => {
  const agents = [
    {
      id: 'architect',
      name: 'Architect Agent',
      badge: 'Step 1: Planning',
      icon: <Compass size={20} color="#2563EB" />,
      role: 'Architecture & System Planning',
      description:
        'Analyzes the project repository, identifies relevant modules and dependency graphs, and produces a structured, step-by-step implementation plan.',
      rules: [
        'Inspects repository architecture and dependencies',
        'Produces structured implementation plan for the Builder',
        'Strictly prohibited from modifying files or running Git commands',
      ],
      workspaceModel: 'Dedicated Workspace (Read-Only Inspection)',
      sandboxModel: 'Isolated Container Environment',
      accentColor: '#2563EB',
    },
    {
      id: 'builder',
      name: 'Builder Agent',
      badge: 'Step 2: Implementation',
      icon: <Hammer size={20} color="#059669" />,
      role: 'Code Implementation',
      description:
        'Faithfully executes the Architect Agent’s plan inside an isolated Git worktree workspace, applying targeted modifications to achieve the engineering goal.',
      rules: [
        'Consumes the Architect plan from previous agent execution',
        'Applies code modifications strictly inside assigned workspace',
        'Strictly prohibited from modifying the primary repository',
      ],
      workspaceModel: 'Dedicated Workspace (Isolated Writable Worktree)',
      sandboxModel: 'Isolated Container Environment',
      accentColor: '#059669',
    },
    {
      id: 'tester',
      name: 'Tester Agent',
      badge: 'Step 3: Verification',
      icon: <CheckCheck size={20} color="#D97706" />,
      role: 'Verification & Quality Assurance',
      description:
        'Verifies the Builder Agent’s implementation by identifying and executing relevant test suites inside a controlled Docker sandbox and returning structured test metrics.',
      rules: [
        'Reviews Builder changes against the original engineering goal',
        'Executes automated test suites in a secured container',
        'Outputs structured metrics (Tests Run, Passed, Failed, Status)',
      ],
      workspaceModel: 'Dedicated Workspace (Verification Worktree)',
      sandboxModel: 'Isolated Container Environment',
      accentColor: '#D97706',
    },
  ];

  return (
    <div className="view-container" style={{ maxWidth: '1080px', margin: '0 auto' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '24px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '4px' }}>
            <h1 style={{ fontSize: '20px', fontWeight: 600, color: '#0F172A', margin: 0 }}>
              Autonomous Agent Team
            </h1>
            <span
              style={{
                fontSize: '11px',
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: '9999px',
                backgroundColor: '#EFF6FF',
                color: '#2563EB',
                border: '1px solid #BFDBFE',
              }}
            >
              Phase 5
            </span>
          </div>
          <p style={{ fontSize: '13px', color: '#64748B', margin: 0 }}>
            {currentProject
              ? `Coordinated sequential agent pipeline for project "${currentProject.name}".`
              : 'Coordinated sequential agent team executing in isolated workspaces and sandboxes.'}
          </p>
        </div>

        {onOpenCreateRun && (
          <button
            className="btn btn-primary btn-sm"
            onClick={onOpenCreateRun}
            style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
          >
            <Plus size={13} />
            <span>New Engineering Run</span>
          </button>
        )}
      </div>

      {/* Sequential Pipeline Flow Diagram */}
      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '8px',
          padding: '16px 20px',
          marginBottom: '24px',
          boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
        }}
      >
        <div style={{ fontSize: '11px', fontWeight: 600, color: '#64748B', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: '12px' }}>
          Sequential Execution Pipeline
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ padding: '6px 10px', backgroundColor: '#F8FAFC', border: '1px solid #E2E8F0', borderRadius: '6px', fontSize: '12px', fontWeight: 600, color: '#0F172A' }}>
              Engineering Goal
            </div>
            <ArrowRight size={14} color="#94A3B8" />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ padding: '6px 10px', backgroundColor: '#EFF6FF', border: '1px solid #BFDBFE', borderRadius: '6px', fontSize: '12px', fontWeight: 600, color: '#2563EB', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Compass size={14} />
              <span>Architect</span>
            </div>
            <ArrowRight size={14} color="#94A3B8" />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ padding: '6px 10px', backgroundColor: '#ECFDF5', border: '1px solid #A7F3D0', borderRadius: '6px', fontSize: '12px', fontWeight: 600, color: '#059669', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Hammer size={14} />
              <span>Builder</span>
            </div>
            <ArrowRight size={14} color="#94A3B8" />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{ padding: '6px 10px', backgroundColor: '#FFFBEB', border: '1px solid #FDE68A', borderRadius: '6px', fontSize: '12px', fontWeight: 600, color: '#D97706', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCheck size={14} />
              <span>Tester</span>
            </div>
            <ArrowRight size={14} color="#94A3B8" />
          </div>

          <div style={{ padding: '6px 10px', backgroundColor: '#F1F5F9', border: '1px solid #CBD5E1', borderRadius: '6px', fontSize: '12px', fontWeight: 600, color: '#334155' }}>
            Verified Results
          </div>
        </div>
      </div>

      {/* Agent Profiles Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '16px', marginBottom: '24px' }}>
        {agents.map((agent) => (
          <div
            key={agent.id}
            style={{
              backgroundColor: '#FFFFFF',
              border: '1px solid #E2E8F0',
              borderRadius: '8px',
              padding: '18px',
              display: 'flex',
              flexDirection: 'column',
              boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
            }}
          >
            {/* Header */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div
                  style={{
                    width: '36px',
                    height: '36px',
                    borderRadius: '8px',
                    backgroundColor: '#F8FAFC',
                    border: '1px solid #E2E8F0',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                  }}
                >
                  {agent.icon}
                </div>
                <div>
                  <div style={{ fontSize: '14px', fontWeight: 600, color: '#0F172A' }}>{agent.name}</div>
                  <div style={{ fontSize: '11px', color: '#64748B' }}>{agent.role}</div>
                </div>
              </div>
              <span
                style={{
                  fontSize: '10px',
                  fontWeight: 600,
                  padding: '2px 6px',
                  borderRadius: '4px',
                  backgroundColor: '#F1F5F9',
                  color: '#475569',
                  border: '1px solid #E2E8F0',
                }}
              >
                {agent.badge}
              </span>
            </div>

            {/* Description */}
            <p style={{ fontSize: '12px', color: '#475569', lineHeight: 1.5, marginBottom: '14px', flexGrow: 1 }}>
              {agent.description}
            </p>

            {/* Rules list */}
            <div style={{ marginBottom: '14px' }}>
              <div style={{ fontSize: '11px', fontWeight: 600, color: '#0F172A', marginBottom: '6px' }}>
                Operational Scope:
              </div>
              <ul style={{ margin: 0, paddingLeft: '16px', fontSize: '11px', color: '#64748B', lineHeight: 1.6 }}>
                {agent.rules.map((rule, idx) => (
                  <li key={idx}>{rule}</li>
                ))}
              </ul>
            </div>

            {/* Environment tags */}
            <div style={{ borderTop: '1px solid #F1F5F9', paddingTop: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#334155' }}>
                <FolderGit2 size={13} color="#059669" />
                <span>{agent.workspaceModel}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: '#334155' }}>
                <Box size={13} color="#2563EB" />
                <span>{agent.sandboxModel}</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Architectural Isolation & Guarantees Panel */}
      <div
        style={{
          backgroundColor: '#FFFFFF',
          border: '1px solid #E2E8F0',
          borderRadius: '8px',
          padding: '16px 20px',
          boxShadow: '0 1px 2px rgba(0,0,0,0.02)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
          <Shield size={16} color="#059669" />
          <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#0F172A', margin: 0 }}>
            Phase 5 Architectural Guarantees & Constraints
          </h3>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '14px', fontSize: '12px', color: '#475569' }}>
          <div>
            <div style={{ fontWeight: 600, color: '#0F172A', marginBottom: '2px' }}>Strict Agent Isolation</div>
            <div style={{ color: '#64748B', fontSize: '11px', lineHeight: 1.4 }}>
              Agents never share writable directories. Each agent receives a dedicated worktree workspace and sandbox.
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 600, color: '#0F172A', marginBottom: '2px' }}>Zero Git Operations by Agents</div>
            <div style={{ color: '#64748B', fontSize: '11px', lineHeight: 1.4 }}>
              Agents cannot execute Git commands. Version control and worktree isolation are managed exclusively by Codex OS.
            </div>
          </div>
          <div>
            <div style={{ fontWeight: 600, color: '#0F172A', marginBottom: '2px' }}>Fail-Fast Policy (No Retries)</div>
            <div style={{ color: '#64748B', fontSize: '11px', lineHeight: 1.4 }}>
              If an agent fails, the workflow immediately halts. Automatic retries and loops are reserved for future phases.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
