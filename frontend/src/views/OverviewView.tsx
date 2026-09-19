import React from 'react';
import { Project, EngineeringRun, HealthResponse } from '../api/types';
import { ProjectCard } from '../components/ProjectCard';
import { RunsTable } from '../components/RunsTable';
import { SystemStatusCard } from '../components/SystemStatusCard';

interface OverviewViewProps {
  currentProject: Project | null;
  runs: EngineeringRun[];
  runsLoading: boolean;
  health: HealthResponse | null;
  healthLoading: boolean;
  onRefreshHealth: () => void;
  onOpenCreateProject: () => void;
  onOpenCreateRun: () => void;
  onDeleteProject: (id: number) => void;
  onSelectRun: (run: EngineeringRun) => void;
  onExecuteRun: (runId: number) => Promise<void>;
}

export const OverviewView: React.FC<OverviewViewProps> = ({
  currentProject,
  runs,
  runsLoading,
  health,
  healthLoading,
  onRefreshHealth,
  onOpenCreateProject,
  onOpenCreateRun,
  onDeleteProject,
  onSelectRun,
  onExecuteRun,
}) => {

  return (
    <div>
      <div className="content-header">
        <div>
          <h1 className="content-title">Engineering Overview</h1>
          <p className="content-subtitle">
            Autonomous software engineering sandbox workspace and active project telemetry.
          </p>
        </div>
      </div>

      <div className="overview-grid">
        {/* Main Column */}
        <div className="overview-main">
          {/* Active Project Card */}
          <ProjectCard
            project={currentProject}
            onDeleteProject={onDeleteProject}
            onOpenCreateProject={onOpenCreateProject}
          />

          {/* Engineering Runs Table */}
          <RunsTable
            runs={runs}
            project={currentProject}
            loading={runsLoading}
            onOpenCreateRun={onOpenCreateRun}
            onSelectRun={onSelectRun}
            onExecuteRun={onExecuteRun}
          />

        </div>

        {/* Aside Column */}
        <div className="overview-aside">
          {/* System Status Matrix */}
          <SystemStatusCard
            health={health}
            loading={healthLoading}
            onRefresh={onRefreshHealth}
          />
        </div>
      </div>
    </div>
  );
};
