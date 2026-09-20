import { useState, useEffect, useCallback } from 'react';
import { api } from './services/api';
import { DashboardStats, Project, Task, User, TaskFilters } from './types';
import { Navbar } from './components/Navbar';
import { DashboardView } from './components/DashboardView';
import { ProjectList } from './components/ProjectList';
import { ProjectDetailModal } from './components/ProjectDetailModal';
import { TaskList } from './components/TaskList';
import { TaskModal } from './components/TaskModal';
import { TaskDetailModal } from './components/TaskDetailModal';
import { LoadingSpinner } from './components/common/LoadingSpinner';
import { ErrorMessage } from './components/common/ErrorMessage';

export function App() {
  const [activeTab, setActiveTab] = useState<'dashboard' | 'projects' | 'tasks'>('dashboard');
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [filters, setFilters] = useState<TaskFilters>({});

  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isBackendConnected, setIsBackendConnected] = useState<boolean>(false);

  // Modals state
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [taskModalOpen, setTaskModalOpen] = useState<boolean>(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);

  const loadData = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Check health
      const healthy = await api.checkHealth();
      setIsBackendConnected(healthy);

      // Concurrent fetch of core data
      const [usersData, projectsData, statsData, tasksData] = await Promise.all([
        api.getUsers(),
        api.getProjects(),
        api.getDashboardStats(),
        api.getTasks(filters),
      ]);

      setUsers(usersData);
      setProjects(projectsData);
      setStats(statsData);
      setTasks(tasksData);
      setIsBackendConnected(true);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to communicate with TaskForge API.');
      setIsBackendConnected(false);
    } finally {
      setIsLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // Project Handlers
  const handleCreateProject = async (data: { name: string; description?: string; status?: string; owner_id: number }) => {
    await api.createProject(data);
    await loadData();
  };

  const handleUpdateProject = async (id: number, data: Partial<Project>) => {
    const updated = await api.updateProject(id, data);
    setSelectedProject(updated);
    await loadData();
  };

  const handleDeleteProject = async (id: number) => {
    await api.deleteProject(id);
    setSelectedProject(null);
    await loadData();
  };

  const handleViewTasksForProject = (projectId: number) => {
    setFilters((prev) => ({ ...prev, project_id: projectId }));
    setActiveTab('tasks');
  };

  // Task Handlers
  const handleCreateOrEditTask = async (data: {
    title: string;
    description?: string;
    status: Task['status'];
    priority: Task['priority'];
    due_date?: string | null;
    project_id: number;
    assignee_id?: number | null;
  }) => {
    if (editingTask) {
      await api.updateTask(editingTask.id, data);
    } else {
      await api.createTask(data);
    }
    setEditingTask(null);
    setTaskModalOpen(false);
    await loadData();
  };

  const handleDeleteTask = async (taskId: number) => {
    await api.deleteTask(taskId);
    setSelectedTask(null);
    await loadData();
  };

  const handleQuickStatusChange = async (taskId: number, newStatus: Task['status']) => {
    try {
      await api.updateTask(taskId, { status: newStatus });
      await loadData();
      if (selectedTask && selectedTask.id === taskId) {
        setSelectedTask((prev) => (prev ? { ...prev, status: newStatus } : null));
      }
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : 'Failed to update status');
    }
  };

  const handleAddComment = async (taskId: number, content: string, authorId: number) => {
    const comment = await api.addComment(taskId, { content, author_id: authorId });
    // Refresh selected task details to include new comment
    const updatedTask = await api.getTask(taskId);
    setSelectedTask(updatedTask);
    await loadData();
    return comment;
  };

  const openEditTaskModal = (task: Task) => {
    setEditingTask(task);
    setTaskModalOpen(true);
  };

  const openCreateTaskModal = () => {
    setEditingTask(null);
    setTaskModalOpen(true);
  };

  const handleOpenTaskDetail = async (task: Task) => {
    try {
      const detailed = await api.getTask(task.id);
      setSelectedTask(detailed);
    } catch {
      setSelectedTask(task);
    }
  };

  return (
    <div className="app-container">
      <Navbar
        activeTab={activeTab}
        onSelectTab={setActiveTab}
        onOpenCreateTask={openCreateTaskModal}
        isBackendConnected={isBackendConnected}
      />

      <main className="main-content">
        {error && <ErrorMessage message={error} onRetry={loadData} />}

        {isLoading && !stats ? (
          <LoadingSpinner message="Connecting to TaskForge services..." />
        ) : (
          <>
            {activeTab === 'dashboard' && stats && (
              <DashboardView
                stats={stats}
                onSelectTask={handleOpenTaskDetail}
                onNavigateTab={setActiveTab}
              />
            )}

            {activeTab === 'projects' && (
              <ProjectList
                projects={projects}
                users={users}
                onSelectProject={setSelectedProject}
                onCreateProject={handleCreateProject}
              />
            )}

            {activeTab === 'tasks' && (
              <TaskList
                tasks={tasks}
                projects={projects}
                filters={filters}
                onFilterChange={setFilters}
                onSelectTask={handleOpenTaskDetail}
                onOpenCreateTask={openCreateTaskModal}
                onQuickStatusChange={handleQuickStatusChange}
              />
            )}
          </>
        )}
      </main>

      {/* Project Detail Modal */}
      {selectedProject && (
        <ProjectDetailModal
          project={selectedProject}
          onClose={() => setSelectedProject(null)}
          onUpdateProject={handleUpdateProject}
          onDeleteProject={handleDeleteProject}
          onViewTasksForProject={handleViewTasksForProject}
        />
      )}

      {/* Task Detail Modal */}
      {selectedTask && (
        <TaskDetailModal
          task={selectedTask}
          users={users}
          onClose={() => setSelectedTask(null)}
          onEdit={openEditTaskModal}
          onDelete={handleDeleteTask}
          onStatusChange={handleQuickStatusChange}
          onAddComment={handleAddComment}
        />
      )}

      {/* Create / Edit Task Modal */}
      {taskModalOpen && (
        <TaskModal
          initialTask={editingTask}
          projects={projects}
          users={users}
          defaultProjectId={typeof filters.project_id === 'number' ? filters.project_id : undefined}
          onClose={() => { setTaskModalOpen(false); setEditingTask(null); }}
          onSubmit={handleCreateOrEditTask}
        />
      )}
    </div>
  );
}

export default App;
