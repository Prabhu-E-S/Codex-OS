import React from 'react';
import {
  FolderGit2,
  Box,
  Cpu,
  Database,
  Clock,
  CheckCircle2,
  AlertCircle,
  PlayCircle,
} from 'lucide-react';
import { ControlRoomWorkspace, ControlRoomSandbox } from '../../api/types';

interface ControlRoomWorkspacesSandboxesProps {
  workspaces: ControlRoomWorkspace[];
  sandboxes: ControlRoomSandbox[];
}

export const ControlRoomWorkspacesSandboxes: React.FC<ControlRoomWorkspacesSandboxesProps> = ({
  workspaces,
  sandboxes,
}) => {
  return (
    <div className="cr-env-container">
      {/* Workspaces Section */}
      <div className="cr-env-section">
        <div className="cr-card-header">
          <div className="cr-card-title-row">
            <FolderGit2 size={16} />
            <h3 className="cr-card-title">Git Worktree Workspaces</h3>
          </div>
          <span className="cr-card-subtitle">
            Isolated worktree directories preventing git lock contention
          </span>
        </div>

        {workspaces.length === 0 ? (
          <div className="cr-empty-card">
            <FolderGit2 size={18} className="text-muted" />
            <span>No workspace information available.</span>
          </div>
        ) : (
          <div className="cr-env-grid">
            {workspaces.map((ws) => (
              <div key={ws.id} className="cr-env-card">
                <div className="env-card-top">
                  <span className="env-name">{ws.name}</span>
                  <span className={`cr-step-status-pill status-${ws.status.toLowerCase()}`}>
                    {ws.status === 'READY' && <CheckCircle2 size={10} />}
                    {ws.status === 'IN_USE' && <PlayCircle size={10} />}
                    <span>{ws.status}</span>
                  </span>
                </div>

                <div className="env-meta-list">
                  <div className="env-meta-row">
                    <span className="label">Branch:</span>
                    <span className="val font-mono">{ws.branch_name}</span>
                  </div>
                  <div className="env-meta-row">
                    <span className="label">Safe Path:</span>
                    <span className="val font-mono text-muted">{ws.relative_path}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Sandboxes Section */}
      <div className="cr-env-section">
        <div className="cr-card-header">
          <div className="cr-card-title-row">
            <Box size={16} />
            <h3 className="cr-card-title">Docker Sandboxes</h3>
          </div>
          <span className="cr-card-subtitle">
            Ephemeral containers executing test suites with restricted CPU, memory, and networking
          </span>
        </div>

        {sandboxes.length === 0 ? (
          <div className="cr-empty-card">
            <Box size={18} className="text-muted" />
            <span>No sandbox information available.</span>
          </div>
        ) : (
          <div className="cr-env-grid">
            {sandboxes.map((sb) => (
              <div key={sb.id} className="cr-env-card">
                <div className="env-card-top">
                  <span className="env-name">{sb.image}</span>
                  <span className={`cr-step-status-pill status-${sb.status.toLowerCase()}`}>
                    {sb.status === 'RUNNING' && <PlayCircle size={10} />}
                    {sb.status === 'STOPPED' && <CheckCircle2 size={10} />}
                    {sb.status === 'FAILED' && <AlertCircle size={10} />}
                    <span>{sb.status}</span>
                  </span>
                </div>

                <div className="env-meta-list">
                  {sb.container_id_preview && (
                    <div className="env-meta-row">
                      <span className="label">Container ID:</span>
                      <span className="val font-mono">{sb.container_id_preview}</span>
                    </div>
                  )}

                  <div className="env-meta-row">
                    <span className="label">Limits:</span>
                    <span className="val">
                      <Cpu size={11} /> {sb.cpu_limit} CPU &bull; <Database size={11} />{' '}
                      {sb.memory_limit}
                    </span>
                  </div>

                  <div className="env-meta-row">
                    <span className="label">Timeout:</span>
                    <span className="val">
                      <Clock size={11} /> {sb.timeout_seconds}s
                    </span>
                  </div>

                  {sb.exit_code !== undefined && sb.exit_code !== null && (
                    <div className="env-meta-row">
                      <span className="label">Last Exit Code:</span>
                      <span className="val font-mono">{sb.exit_code}</span>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
