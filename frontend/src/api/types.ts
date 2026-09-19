export interface Project {
  id: number;
  name: string;
  repository_path: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  runs_count: number;
}

export interface CreateProjectPayload {
  name: string;
  repository_path: string;
  description?: string;
}

export interface Workspace {
  id: number;
  project_id: number;
  name: string;
  path: string;
  branch_name: string;
  status: 'CREATING' | 'READY' | 'IN_USE' | 'ERROR' | 'REMOVING' | 'REMOVED' | string;
  error_message: string | null;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
}

export interface CreateWorkspacePayload {
  name: string;
}

export interface EngineeringRun {
  id: number;
  project_id: number;
  workspace_id?: number | null;
  workspace_name?: string | null;
  sandbox_id?: number | null;
  status: 'PENDING' | 'STARTING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED' | 'TIMEOUT' | string;
  goal: string;
  started_at: string | null;
  completed_at: string | null;
  exit_code: number | null;
  stdout: string | null;
  stderr: string | null;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface RunLogsResponse {
  id: number;
  status: string;
  workspace_id?: number | null;
  workspace_name?: string | null;
  sandbox_id?: number | null;
  stdout: string;
  stderr: string;
  exit_code: number | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
}

export interface CreateRunPayload {
  goal: string;
  status?: string;
  workspace_id?: number | null;
  sandbox_id?: number | null;
}

export interface Sandbox {
  id: number;
  workspace_id: number;
  container_id: string | null;
  image: string;
  status: 'CREATING' | 'CREATED' | 'STARTING' | 'RUNNING' | 'STOPPING' | 'STOPPED' | 'FAILED' | 'REMOVED' | string;
  cpu_limit: number;
  memory_limit: string;
  timeout_seconds: number;
  network_enabled: boolean;
  pids_limit: number;
  exit_code: number | null;
  error_message: string | null;
  started_at: string | null;
  stopped_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface SandboxCreatePayload {
  image?: string;
  cpu_limit?: number;
  memory_limit?: string;
  timeout_seconds?: number;
  network_enabled?: boolean;
  pids_limit?: number;
}

export interface SandboxExecutePayload {
  command: string;
  timeout?: number;
}

export interface CommandResult {
  exit_code: number;
  stdout: string;
  stderr: string;
  duration_ms: number;
  timed_out: boolean;
  error_message: string | null;
}

export interface DockerStatusResponse {
  available: boolean;
  message: string;
  provider: string;
}


export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error';
  service: string;
  version: string;
  phase: number;
  database: 'connected' | 'disconnected';
  database_dialect?: string | null;
  database_error?: string | null;
}

export type AgentType = 'ARCHITECT' | 'BUILDER' | 'TESTER';

export type AgentStatus = 'PENDING' | 'STARTING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED';

export interface AgentExecution {
  id: number;
  engineering_run_id: number;
  agent_type: AgentType;
  agent_name: string;
  workspace_id: number | null;
  workspace_name: string | null;
  sandbox_id: number | null;
  status: AgentStatus;
  input_summary: string | null;
  output: string;
  error_message: string | null;
  exit_code: number | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface AgentWorkflowStatusResponse {
  run_id: number;
  run_status: string;
  active_agent: string | null;
  agents: AgentExecution[];
}

