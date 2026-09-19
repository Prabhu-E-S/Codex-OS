import React, { useState, useEffect, useCallback } from 'react';
import { Header } from './components/Header';
import { Sidebar, NavTab } from './components/Sidebar';
import { OverviewView } from './views/OverviewView';
import { ControlRoomView } from './views/ControlRoomView';
import { WorkspacesView } from './views/WorkspacesView';
import { AgentsView } from './views/AgentsView';
import { EvaluationsView } from './views/EvaluationsView';
import { PlaceholderView } from './components/PlaceholderView';
import { CreateProjectModal } from './components/CreateProjectModal';
import { CreateRunModal } from './components/CreateRunModal';
import { RunDetailModal } from './components/RunDetailModal';
import { api } from './api/client';
import { Project, EngineeringRun, HealthResponse, CreateProjectPayload, CreateRunPayload } from './api/types';
import { AlertCircle } from 'lucide-react';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<NavTab>('overview');
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<number | null>(null);
  const [runs, setRuns] = useState<EngineeringRun[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);

  const [loadingProjects, setLoadingProjects] = useState(true);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [loadingHealth, setLoadingHealth] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);

  const [isCreateProjectOpen, setIsCreateProjectOpen] = useState(false);
  const [isCreateRunOpen, setIsCreateRunOpen] = useState(false);
  const [selectedRunForDetails, setSelectedRunForDetails] = useState<EngineeringRun | null>(null);
  const [selectedRunIdForControlRoom, setSelectedRunIdForControlRoom] = useState<number | null>(null);
  const [isRunDetailOpen, setIsRunDetailOpen] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);


  // Fetch health check
  const fetchHealth = useCallback(async () => {
    setLoadingHealth(true);
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch {
      setHealth(null);
    } finally {
      setLoadingHealth(false);
    }
  }, []);

  // Fetch all projects
  const fetchProjects = useCallback(async (selectId?: number) => {
    setLoadingProjects(true);
    try {
      const data = await api.getProjects();
      setProjects(data);
      if (data.length > 0) {
        if (selectId && data.some((p) => p.id === selectId)) {
          setSelectedProjectId(selectId);
        } else if (!selectedProjectId || !data.some((p) => p.id === selectedProjectId)) {
          setSelectedProjectId(data[0].id);
        }
      } else {
        setSelectedProjectId(null);
        setRuns([]);
      }
      setGlobalError(null);
    } catch (err: unknown) {
      if (err instanceof Error) {
        setGlobalError(`Backend communication error: ${err.message}`);
      } else {
        setGlobalError('Backend communication error');
      }
    } finally {
      setLoadingProjects(false);
    }
  }, [selectedProjectId]);

  // Fetch runs for the selected project
  const fetchRuns = useCallback(async (projectId: number) => {
    setLoadingRuns(true);
    try {
      const data = await api.getProjectRuns(projectId);
      setRuns(data);
    } catch (err: unknown) {
      console.error('Failed to load runs:', err);
      setRuns([]);
    } finally {
      setLoadingRuns(false);
    }
  }, []);

  // Initial load
  useEffect(() => {
    fetchHealth();
    fetchProjects();
  }, [fetchHealth, fetchProjects]);

  // Load runs when selected project changes
  useEffect(() => {
    if (selectedProjectId) {
      fetchRuns(selectedProjectId);
    } else {
      setRuns([]);
    }
  }, [selectedProjectId, fetchRuns]);

  // Handler for creating a project
  const handleCreateProject = async (payload: CreateProjectPayload) => {
    const newProject = await api.createProject(payload);
    await fetchProjects(newProject.id);
  };

  // Handler for deleting a project
  const handleDeleteProject = async (id: number) => {
    try {
      await api.deleteProject(id);
      await fetchProjects();
    } catch (err: unknown) {
      if (err instanceof Error) {
        alert(`Failed to delete project: ${err.message}`);
      }
    }
  };

  // Handler for recording a run
  const handleCreateRun = async (projectId: number, payload: CreateRunPayload) => {
    const newRun = await api.createRun(projectId, payload);
    await fetchRuns(projectId);
    await fetchProjects(projectId);
    setSelectedRunForDetails(newRun);
    setIsRunDetailOpen(true);
  };

  // Handler for selecting a run to inspect logs / details
  const handleSelectRun = (run: EngineeringRun) => {
    setSelectedRunForDetails(run);
    setIsRunDetailOpen(true);
  };

  // Handler for triggering run execution
  const handleExecuteRun = async (runId: number) => {
    try {
      const updated = await api.executeRun(runId);
      setSelectedRunForDetails(updated);
      setIsRunDetailOpen(true);
      if (selectedProjectId) {
        await fetchRuns(selectedProjectId);
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to execute run');
    }
  };

  // Handler when a run status or log is updated from the modal
  const handleRunUpdated = (updatedRun: EngineeringRun) => {
    setSelectedRunForDetails(updatedRun);
    setRuns((prev) => prev.map((r) => (r.id === updatedRun.id ? updatedRun : r)));
    if (selectedProjectId) {
      fetchRuns(selectedProjectId);
    }
  };

  // Handler for opening a run directly in the Control Room
  const handleOpenControlRoom = (runId: number) => {
    setSelectedRunIdForControlRoom(runId);
    setActiveTab('control-room');
  };

  const currentProject = projects.find((p) => p.id === selectedProjectId) || null;

  return (
    <div className="app-shell">
      <Header
        projects={projects}
        selectedProjectId={selectedProjectId}
        onSelectProject={(id) => setSelectedProjectId(id)}
        onOpenCreateProject={() => setIsCreateProjectOpen(true)}
        mobileMenuOpen={mobileMenuOpen}
        onToggleMobileMenu={() => setMobileMenuOpen(!mobileMenuOpen)}
      />

      <div className="shell-body">
        <Sidebar
          activeTab={activeTab}
          onSelectTab={(tab) => setActiveTab(tab)}
          mobileMenuOpen={mobileMenuOpen}
          onCloseMobileMenu={() => setMobileMenuOpen(false)}
        />

        <main className="main-viewport">
          {globalError && (
            <div className="alert-banner alert-banner-error" style={{ marginBottom: '20px' }}>
              <AlertCircle size={16} />
              <span>{globalError}. Ensure the FastAPI server is running on port 8000.</span>
            </div>
          )}

          {health === null && !loadingHealth && !loadingProjects && (
            <div className="alert-banner alert-banner-error" style={{ marginBottom: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <AlertCircle size={16} />
                <span>Backend unavailable — ensure FastAPI server is running on port 8000.</span>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={() => { fetchHealth(); fetchProjects(); }}>Retry</button>
            </div>
          )}

          {activeTab === 'overview' ? (
            loadingProjects && projects.length === 0 ? (
              <div className="empty-state" style={{ padding: '48px' }}>
                <div className="empty-desc">Loading Codex OS environment...</div>
              </div>
            ) : (
              <OverviewView
                currentProject={currentProject}
                runs={runs}
                runsLoading={loadingRuns}
                health={health}
                healthLoading={loadingHealth}
                onRefreshHealth={fetchHealth}
                onOpenCreateProject={() => setIsCreateProjectOpen(true)}
                onOpenCreateRun={() => setIsCreateRunOpen(true)}
                onDeleteProject={handleDeleteProject}
                onSelectRun={handleSelectRun}
                onExecuteRun={handleExecuteRun}
                onOpenControlRoom={handleOpenControlRoom}
              />
            )
          ) : activeTab === 'control-room' ? (
            <ControlRoomView
              currentProject={currentProject}
              runs={runs}
              selectedRunId={selectedRunIdForControlRoom}
              onSelectRunId={(id) => setSelectedRunIdForControlRoom(id)}
              onOpenEvaluationsView={() => setActiveTab('evaluations')}
              onOpenCreateRun={() => setIsCreateRunOpen(true)}
            />
          ) : activeTab === 'workspaces' ? (
            <WorkspacesView currentProject={currentProject} />
          ) : activeTab === 'agents' ? (
            <AgentsView
              currentProject={currentProject}
              onOpenCreateRun={() => setIsCreateRunOpen(true)}
            />
          ) : activeTab === 'evaluations' ? (
            <EvaluationsView
              currentProject={currentProject}
              onSelectRun={(runId) => {
                const r = runs.find((item) => item.id === runId);
                if (r) {
                  handleSelectRun(r);
                }
              }}
            />
          ) : (
            <PlaceholderView
              tab={activeTab}
              onBackToOverview={() => setActiveTab('overview')}
            />
          )}
        </main>
      </div>

      {/* Modals */}
      <CreateProjectModal
        isOpen={isCreateProjectOpen}
        onClose={() => setIsCreateProjectOpen(false)}
        onSubmit={handleCreateProject}
      />

      <CreateRunModal
        isOpen={isCreateRunOpen}
        project={currentProject}
        onClose={() => setIsCreateRunOpen(false)}
        onSubmit={handleCreateRun}
      />

      <RunDetailModal
        isOpen={isRunDetailOpen}
        run={selectedRunForDetails}
        onClose={() => setIsRunDetailOpen(false)}
        onRunUpdated={handleRunUpdated}
        onOpenControlRoom={handleOpenControlRoom}
      />
    </div>
  );
};


export default App;
