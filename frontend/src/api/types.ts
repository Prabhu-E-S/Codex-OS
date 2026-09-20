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
  docker?: 'available' | 'unavailable' | string;
  docker_error?: string | null;
  codex?: 'available' | 'unavailable' | string;
  codex_command?: string | null;
  codex_error?: string | null;
}

export type AgentType = 'ARCHITECT' | 'BUILDER' | 'TESTER' | 'BREAKER' | 'SECURITY';

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
  iteration?: number;
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

export type FindingType = 'BREAKER' | 'SECURITY';

export type FindingSeverity = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';

export type FindingCategory =
  | 'EDGE_CASE'
  | 'INPUT_VALIDATION'
  | 'ERROR_HANDLING'
  | 'API_BEHAVIOR'
  | 'DATA_HANDLING'
  | 'REGRESSION'
  | 'PERFORMANCE'
  | 'AUTHENTICATION'
  | 'AUTHORIZATION'
  | 'DEPENDENCY'
  | 'SECRET'
  | 'INJECTION'
  | 'CONFIGURATION'
  | 'FILESYSTEM'
  | 'OTHER'
  | string;

export interface Finding {
  id: number;
  engineering_run_id: number;
  agent_execution_id: number | null;
  iteration?: number;
  type: FindingType;
  severity: FindingSeverity;
  category: FindingCategory;
  title: string;
  description: string;
  file_path: string | null;
  line_number: number | null;
  evidence: string | null;
  reproduction: string | null;
  remediation: string | null;
  status: 'OPEN' | 'CONFIRMED' | 'RESOLVED' | 'DISMISSED' | string;
  resolved_iteration?: number | null;
  resolved_at?: string | null;
  created_at: string;
  updated_at: string;
}

export interface FindingsSummary {
  total: number;
  breaker_count: number;
  security_count: number;
  open_count?: number;
  resolved_count?: number;
  by_severity: Record<string, number>;
  by_category: Record<string, number>;
}

// Phase 7 — Autonomous Orchestrator Types
export type WorkflowState =
  | 'PENDING'
  | 'ARCHITECTING'
  | 'BUILDING'
  | 'TESTING'
  | 'BREAKING'
  | 'SECURITY_SCANNING'
  | 'DECIDING'
  | 'ITERATING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED'
  | 'PAUSED';

export type OrchestratorDecision =
  | 'CONTINUE'
  | 'RETRY_BUILDER'
  | 'STOP_SUCCESS'
  | 'STOP_FAILURE'
  | 'PAUSE'
  | 'CANCELLED';

export interface OrchestrationEvent {
  event_type: string;
  run_id: number;
  iteration: number;
  timestamp: string;
  agent?: string | null;
  state?: string | null;
  decision?: string | null;
  reason?: string | null;
  details?: Record<string, unknown> | null;
}

export interface OrchestrationResponse {
  id: number;
  engineering_run_id: number;
  state: WorkflowState;
  current_agent: string | null;
  iteration: number;
  max_iterations: number;
  last_decision: OrchestratorDecision | null;
  last_decision_reason: string | null;
  pause_requested: boolean;
  cancel_requested: boolean;
  failure_reason: string | null;
  events: OrchestrationEvent[];
  created_at: string;
  updated_at: string;
}

export interface StartAutonomousRunPayload {
  max_iterations?: number;
}

// Evaluation & Engineering Score (Phase 8)
export type EvaluationDimensionType =
  | 'CORRECTNESS'
  | 'TEST_COVERAGE'
  | 'SECURITY'
  | 'MAINTAINABILITY'
  | 'PERFORMANCE'
  | 'REGRESSION_RISK';

export type DimensionStatus = 'STRONG' | 'ADEQUATE' | 'WEAK' | 'INSUFFICIENT_EVIDENCE';

export type EvaluationStatus = 'PENDING' | 'COLLECTING_EVIDENCE' | 'EVALUATING' | 'COMPLETED' | 'FAILED';

export interface EvaluationEvidence {
  id: number;
  evaluation_id: number;
  dimension: string;
  source_type: string;
  source_id?: string | null;
  metric_name: string;
  metric_value?: string | null;
  unit?: string | null;
  description: string;
  evidence_text?: string | null;
  file_path?: string | null;
  line_number?: number | null;
  created_at: string;
}

export interface EvaluationDimension {
  id: number;
  evaluation_id: number;
  dimension: EvaluationDimensionType;
  score?: number | null;
  status: DimensionStatus;
  weight: number;
  weighted_score?: number | null;
  explanation: string;
  metrics: Record<string, unknown>;
  limitations?: string | null;
  created_at: string;
}

export interface Evaluation {
  id: number;
  engineering_run_id: number;
  status: EvaluationStatus;
  overall_score?: number | null;
  status_label: DimensionStatus;
  score_version: string;
  weights: Record<string, number>;
  formula?: string | null;
  summary?: string | null;
  strengths: string[];
  weaknesses: string[];
  limitations: string[];
  started_at?: string | null;
  completed_at?: string | null;
  error_message?: string | null;
  created_at: string;
  updated_at: string;
  dimensions?: EvaluationDimension[];
  evidence_items?: EvaluationEvidence[];
}

export interface EvaluateRunPayload {
  weights?: Record<string, number>;
}

// Phase 9 — Control Room Types
export interface ControlRoomRun {
  id: number;
  project_id: number;
  project_name: string;
  status: string;
  goal: string;
  mode: 'AUTONOMOUS' | 'MANUAL';
  iteration: number;
  max_iterations: number;
  started_at?: string | null;
  completed_at?: string | null;
  duration_seconds?: number | null;
  exit_code?: number | null;
  error_message?: string | null;
  workspace_id?: number | null;
  workspace_name?: string | null;
  sandbox_id?: number | null;
  created_at: string;
  updated_at: string;
}

export interface ControlRoomOrchestration {
  state: WorkflowState;
  current_agent?: string | null;
  iteration: number;
  max_iterations: number;
  last_decision?: string | null;
  last_decision_reason?: string | null;
  failure_reason?: string | null;
  pause_requested: boolean;
  cancel_requested: boolean;
  is_active: boolean;
}

export interface ControlRoomAgent {
  id: number;
  agent_type: string;
  agent_name: string;
  status: string;
  iteration: number;
  workspace_id?: number | null;
  workspace_name?: string | null;
  sandbox_id?: number | null;
  sandbox_status?: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  duration_seconds?: number | null;
  input_summary?: string | null;
  output: string;
  error_message?: string | null;
  exit_code?: number | null;
  findings_count: number;
}

export interface ControlRoomIterationAgentSummary {
  agent_type: string;
  agent_name: string;
  status: string;
  duration_seconds?: number | null;
  findings_count: number;
}

export interface ControlRoomIteration {
  iteration_number: number;
  status: 'COMPLETED' | 'FAILED' | 'RUNNING' | 'RETRYING';
  agents: ControlRoomIterationAgentSummary[];
  decision?: string | null;
  decision_reason?: string | null;
  findings_count: number;
}

export interface ControlRoomWorkspace {
  id: number;
  name: string;
  branch_name: string;
  relative_path: string;
  status: string;
  agent_name?: string | null;
}

export interface ControlRoomSandbox {
  id: number;
  workspace_id: number;
  image: string;
  status: string;
  container_id_preview?: string | null;
  cpu_limit: number;
  memory_limit: string;
  timeout_seconds: number;
  exit_code?: number | null;
  started_at?: string | null;
  stopped_at?: string | null;
}

export interface ControlRoomFinding {
  id: number;
  type: 'BREAKER' | 'SECURITY';
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO';
  category: string;
  title: string;
  description: string;
  file_path?: string | null;
  line_number?: number | null;
  evidence?: string | null;
  reproduction?: string | null;
  remediation?: string | null;
  status: string;
  iteration: number;
  resolved_iteration?: number | null;
  resolved_at?: string | null;
  agent_type?: string | null;
  created_at: string;
}

export interface ControlRoomFindingsSummary {
  total: number;
  by_severity: Record<string, number>;
  by_type: Record<string, number>;
  open: number;
  resolved: number;
}

export interface ControlRoomDimension {
  dimension: string;
  score?: number | null;
  status: DimensionStatus;
  weight: number;
  weighted_score?: number | null;
  explanation?: string | null;
  limitations?: string | null;
}

export interface ControlRoomEvaluation {
  id: number;
  status: string;
  overall_score?: number | null;
  status_label: DimensionStatus;
  score_version: string;
  formula?: string | null;
  summary?: string | null;
  strengths: string[];
  weaknesses: string[];
  limitations: string[];
  dimensions: ControlRoomDimension[];
  evaluated_at?: string | null;
}

export interface ControlRoomEvent {
  timestamp: string;
  event_type: string;
  iteration: number;
  agent?: string | null;
  state?: string | null;
  decision?: string | null;
  reason?: string | null;
  details?: Record<string, unknown> | null;
}

export interface ControlRoomLogs {
  stdout: string;
  stderr: string;
  exit_code?: number | null;
  total_lines: number;
}

export interface ControlRoomSnapshotResponse {
  run: ControlRoomRun;
  orchestration?: ControlRoomOrchestration | null;
  agents: ControlRoomAgent[];
  iterations: ControlRoomIteration[];
  workspaces: ControlRoomWorkspace[];
  sandboxes: ControlRoomSandbox[];
  findings: ControlRoomFinding[];
  findings_summary: ControlRoomFindingsSummary;
  evaluation?: ControlRoomEvaluation | null;
  recent_events: ControlRoomEvent[];
  logs: ControlRoomLogs;
}
