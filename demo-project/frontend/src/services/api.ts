import { DashboardStats, Project, Task, Comment, User, TaskFilters } from '../types';

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `${BASE_URL}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...(options.headers || {}),
  };

  const response = await fetch(url, { ...options, headers });

  if (response.status === 204) {
    return {} as T;
  }

  if (!response.ok) {
    let errorMessage = `HTTP error ${response.status}: ${response.statusText}`;
    try {
      const errorData = await response.json();
      if (errorData.detail) {
        if (typeof errorData.detail === 'string') {
          errorMessage = errorData.detail;
        } else if (Array.isArray(errorData.detail)) {
          errorMessage = errorData.detail.map((d: { msg?: string }) => d.msg || JSON.stringify(d)).join(', ');
        }
      }
    } catch {
      // Non-json response
    }
    throw new Error(errorMessage);
  }

  return response.json();
}

export const api = {
  // Health
  checkHealth: () => fetch('/health').then(r => r.ok).catch(() => false),

  // Dashboard
  getDashboardStats: (): Promise<DashboardStats> => request<DashboardStats>('/dashboard/stats'),

  // Users
  getUsers: (): Promise<User[]> => request<User[]>('/users'),
  createUser: (user: Partial<User>): Promise<User> =>
    request<User>('/users', { method: 'POST', body: JSON.stringify(user) }),

  // Projects
  getProjects: (): Promise<Project[]> => request<Project[]>('/projects'),
  getProject: (id: number): Promise<Project> => request<Project>(`/projects/${id}`),
  createProject: (project: { name: string; description?: string; status?: string; owner_id: number }): Promise<Project> =>
    request<Project>('/projects', { method: 'POST', body: JSON.stringify(project) }),
  updateProject: (id: number, project: Partial<Project>): Promise<Project> =>
    request<Project>(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(project) }),
  deleteProject: (id: number): Promise<void> =>
    request<void>(`/projects/${id}`, { method: 'DELETE' }),

  // Tasks
  getTasks: (filters?: TaskFilters): Promise<Task[]> => {
    const params = new URLSearchParams();
    if (filters?.status) params.append('status', filters.status);
    if (filters?.priority) params.append('priority', filters.priority);
    if (filters?.project_id) params.append('project_id', String(filters.project_id));
    if (filters?.search) params.append('search', filters.search);

    const queryString = params.toString() ? `?${params.toString()}` : '';
    return request<Task[]>(`/tasks${queryString}`);
  },
  getTask: (id: number): Promise<Task> => request<Task>(`/tasks/${id}`),
  createTask: (task: {
    title: string;
    description?: string;
    status?: string;
    priority?: string;
    due_date?: string | null;
    project_id: number;
    assignee_id?: number | null;
  }): Promise<Task> => request<Task>('/tasks', { method: 'POST', body: JSON.stringify(task) }),
  updateTask: (id: number, task: Partial<Task>): Promise<Task> =>
    request<Task>(`/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(task) }),
  deleteTask: (id: number): Promise<void> =>
    request<void>(`/tasks/${id}`, { method: 'DELETE' }),

  // Comments
  addComment: (taskId: number, comment: { content: string; author_id: number }): Promise<Comment> =>
    request<Comment>(`/tasks/${taskId}/comments`, { method: 'POST', body: JSON.stringify(comment) }),
  getTaskComments: (taskId: number): Promise<Comment[]> =>
    request<Comment[]>(`/tasks/${taskId}/comments`),
};
