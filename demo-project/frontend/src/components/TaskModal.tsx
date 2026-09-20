import React, { useState } from 'react';
import { Task, Project, User } from '../types';
import { Button } from './common/Button';

interface TaskModalProps {
  initialTask?: Task | null;
  projects: Project[];
  users: User[];
  defaultProjectId?: number;
  onClose: () => void;
  onSubmit: (data: {
    title: string;
    description?: string;
    status: Task['status'];
    priority: Task['priority'];
    due_date?: string | null;
    project_id: number;
    assignee_id?: number | null;
  }) => Promise<void>;
}

export const TaskModal: React.FC<TaskModalProps> = ({
  initialTask,
  projects,
  users,
  defaultProjectId,
  onClose,
  onSubmit,
}) => {
  const [title, setTitle] = useState(initialTask?.title || '');
  const [description, setDescription] = useState(initialTask?.description || '');
  const [status, setStatus] = useState<Task['status']>(initialTask?.status || 'todo');
  const [priority, setPriority] = useState<Task['priority']>(initialTask?.priority || 'medium');
  const [projectId, setProjectId] = useState<number | ''>(
    initialTask?.project_id || defaultProjectId || projects[0]?.id || ''
  );
  const [assigneeId, setAssigneeId] = useState<number | ''>(
    initialTask?.assignee_id || ''
  );
  
  // Format due date for datetime-local input
  const initialDueDate = initialTask?.due_date 
    ? new Date(initialTask.due_date).toISOString().slice(0, 16) 
    : '';
  const [dueDate, setDueDate] = useState<string>(initialDueDate);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Task title is required.');
      return;
    }
    if (!projectId) {
      setError('Project selection is required.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onSubmit({
        title: title.trim(),
        description: description.trim() || undefined,
        status,
        priority,
        due_date: dueDate ? new Date(dueDate).toISOString() : null,
        project_id: Number(projectId),
        assignee_id: assigneeId ? Number(assigneeId) : null,
      });
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save task.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">{initialTask ? 'Edit Task' : 'Create New Task'}</h2>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        {error && (
          <div style={{ color: '#f87171', background: 'rgba(239, 68, 68, 0.1)', padding: '0.75rem', borderRadius: 'var(--radius-md)', marginBottom: '1rem', fontSize: '0.875rem' }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label className="form-label">Task Title *</label>
            <input
              type="text"
              className="form-input"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Implement user authentication service"
              required
            />
          </div>

          <div className="form-group">
            <label className="form-label">Description</label>
            <textarea
              className="form-textarea"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Technical specifications, context, edge cases..."
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Project *</label>
              <select
                className="form-select"
                value={projectId}
                onChange={(e) => setProjectId(e.target.value ? Number(e.target.value) : '')}
                required
              >
                <option value="" disabled>Select Project</option>
                {projects.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Assignee</label>
              <select
                className="form-select"
                value={assigneeId}
                onChange={(e) => setAssigneeId(e.target.value ? Number(e.target.value) : '')}
              >
                <option value="">Unassigned</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
            <div className="form-group">
              <label className="form-label">Status</label>
              <select
                className="form-select"
                value={status}
                onChange={(e) => setStatus(e.target.value as Task['status'])}
              >
                <option value="todo">To Do</option>
                <option value="in_progress">In Progress</option>
                <option value="review">Review</option>
                <option value="done">Done</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Priority</label>
              <select
                className="form-select"
                value={priority}
                onChange={(e) => setPriority(e.target.value as Task['priority'])}
              >
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </div>
          </div>

          <div className="form-group">
            <label className="form-label">Due Date & Time</label>
            <input
              type="datetime-local"
              className="form-input"
              value={dueDate}
              onChange={(e) => setDueDate(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.5rem' }}>
            <Button type="button" variant="secondary" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" isLoading={isSubmitting}>
              {initialTask ? 'Save Changes' : 'Create Task'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
};
