export interface User {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'manager' | 'member';
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Project {
  id: number;
  name: string;
  description: string | null;
  status: 'active' | 'completed' | 'archived';
  owner_id: number;
  created_at: string;
  updated_at: string;
  task_count?: number;
  owner?: User;
}

export interface Task {
  id: number;
  title: string;
  description: string | null;
  status: 'todo' | 'in_progress' | 'review' | 'done';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  due_date: string | null;
  project_id: number;
  assignee_id: number | null;
  created_at: string;
  updated_at: string;
  project_name?: string | null;
  assignee?: User | null;
  is_overdue?: boolean;
  comment_count?: number;
  comments?: Comment[];
}

export interface Comment {
  id: number;
  content: string;
  task_id: number;
  author_id: number;
  author?: User | null;
  created_at: string;
  updated_at: string;
}

export interface DashboardStats {
  total_projects: number;
  total_tasks: number;
  completed_tasks: number;
  pending_tasks: number;
  overdue_tasks: number;
  tasks_by_priority: Record<string, number>;
  tasks_by_status: Record<string, number>;
  recent_tasks: Task[];
  recent_projects: Project[];
}

export interface TaskFilters {
  status?: string;
  priority?: string;
  project_id?: number | '';
  search?: string;
}
