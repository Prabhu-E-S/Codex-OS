import {
  Project,
  CreateProjectPayload,
  EngineeringRun,
  CreateRunPayload,
  HealthResponse,
  RunLogsResponse,
  Workspace,
  CreateWorkspacePayload,
  Sandbox,
  SandboxCreatePayload,
  SandboxExecutePayload,
  CommandResult,
  DockerStatusResponse,
} from './types';


// Support both VITE_API_URL and NEXT_PUBLIC_API_URL environment variables
const API_BASE = 
  (typeof import.meta !== 'undefined' && import.meta.env?.VITE_API_URL) ||
  (typeof import.meta !== 'undefined' && import.meta.env?.NEXT_PUBLIC_API_URL) ||
  '';

const API_PREFIX = `${API_BASE}/api`;

async function request<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const url = `${API_PREFIX}${endpoint}`;
  
  const headers = {
    'Content-Type': 'application/json',
    ...(options?.headers || {}),
  };

  try {
    const res = await fetch(url, {
      ...options,
      headers,
    });

    if (res.status === 204) {
      return null as unknown as T;
    }

    if (!res.ok) {
      let errorMessage = `Request failed with status ${res.status}`;
      try {
        const errorData = await res.json();
        errorMessage = errorData.detail || errorData.message || errorMessage;
      } catch {
        // Fallback to status text
        errorMessage = res.statusText || errorMessage;
      }
      throw new Error(errorMessage);
    }

    return await res.json();
  } catch (err: unknown) {
    if (err instanceof Error) {
      throw err;
    }
    throw new Error('An unexpected network error occurred');
  }
}

export const api = {
  // Health
  getHealth: (): Promise<HealthResponse> => request<HealthResponse>('/health'),

  // Projects
  getProjects: (): Promise<Project[]> => request<Project[]>('/projects'),
  getProject: (id: number): Promise<Project> => request<Project>(`/projects/${id}`),
  createProject: (payload: CreateProjectPayload): Promise<Project> => 
    request<Project>('/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  deleteProject: (id: number): Promise<void> => 
    request<void>(`/projects/${id}`, {
      method: 'DELETE',
    }),

  // Engineering Runs
  getProjectRuns: (projectId: number): Promise<EngineeringRun[]> => 
    request<EngineeringRun[]>(`/projects/${projectId}/runs`),
  createRun: (projectId: number, payload: CreateRunPayload): Promise<EngineeringRun> => 
    request<EngineeringRun>(`/projects/${projectId}/runs`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getRun: (id: number): Promise<EngineeringRun> => request<EngineeringRun>(`/runs/${id}`),
  executeRun: (id: number): Promise<EngineeringRun> => 
    request<EngineeringRun>(`/runs/${id}/execute`, {
      method: 'POST',
    }),
  cancelRun: (id: number): Promise<EngineeringRun> => 
    request<EngineeringRun>(`/runs/${id}/cancel`, {
      method: 'POST',
    }),
  getRunLogs: (id: number): Promise<RunLogsResponse> => 
    request<RunLogsResponse>(`/runs/${id}/logs`),

  // Git Worktrees (Phase 3)
  getProjectWorkspaces: (projectId: number): Promise<Workspace[]> =>
    request<Workspace[]>(`/projects/${projectId}/workspaces`),
  createWorkspace: (projectId: number, payload: CreateWorkspacePayload): Promise<Workspace> =>
    request<Workspace>(`/projects/${projectId}/workspaces`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  getWorkspace: (workspaceId: number): Promise<Workspace> =>
    request<Workspace>(`/workspaces/${workspaceId}`),
  deleteWorkspace: (workspaceId: number): Promise<Workspace> =>
    request<Workspace>(`/workspaces/${workspaceId}`, {
      method: 'DELETE',
    }),

  // Docker Sandboxes (Phase 4)
  getDockerStatus: (): Promise<DockerStatusResponse> =>
    request<DockerStatusResponse>('/sandboxes/status'),
  createSandbox: (workspaceId: number, payload?: SandboxCreatePayload): Promise<Sandbox> =>
    request<Sandbox>(`/workspaces/${workspaceId}/sandbox`, {
      method: 'POST',
      body: JSON.stringify(payload || {}),
    }),
  getWorkspaceSandbox: (workspaceId: number): Promise<Sandbox | null> =>
    request<Sandbox | null>(`/workspaces/${workspaceId}/sandbox`),
  getSandbox: (sandboxId: number): Promise<Sandbox> =>
    request<Sandbox>(`/sandboxes/${sandboxId}`),
  startSandbox: (sandboxId: number): Promise<Sandbox> =>
    request<Sandbox>(`/sandboxes/${sandboxId}/start`, {
      method: 'POST',
    }),
  stopSandbox: (sandboxId: number): Promise<Sandbox> =>
    request<Sandbox>(`/sandboxes/${sandboxId}/stop`, {
      method: 'POST',
    }),
  deleteSandbox: (sandboxId: number): Promise<Sandbox> =>
    request<Sandbox>(`/sandboxes/${sandboxId}`, {
      method: 'DELETE',
    }),
  executeSandboxCommand: (sandboxId: number, payload: SandboxExecutePayload): Promise<CommandResult> =>
    request<CommandResult>(`/sandboxes/${sandboxId}/execute`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
};

