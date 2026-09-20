import React from 'react';
import { Task, Project, TaskFilters } from '../types';
import { TaskCard } from './TaskCard';
import { EmptyState } from './common/EmptyState';
import { Button } from './common/Button';

interface TaskListProps {
  tasks: Task[];
  projects: Project[];
  filters: TaskFilters;
  onFilterChange: (filters: TaskFilters) => void;
  onSelectTask: (task: Task) => void;
  onOpenCreateTask: () => void;
  onQuickStatusChange: (taskId: number, status: Task['status']) => void;
}

export const TaskList: React.FC<TaskListProps> = ({
  tasks,
  projects,
  filters,
  onFilterChange,
  onSelectTask,
  onOpenCreateTask,
  onQuickStatusChange,
}) => {
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <div>
          <h1 style={{ fontSize: '1.875rem', fontWeight: 800, letterSpacing: '-0.03em', marginBottom: '0.25rem' }}>
            Task Board
          </h1>
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem' }}>
            Organize, prioritize, and assign engineering action items.
          </p>
        </div>
        <Button onClick={onOpenCreateTask}>
          + New Task
        </Button>
      </div>

      {/* Filter Toolbar */}
      <div className="filter-bar">
        {/* Search */}
        <div className="search-input-wrapper">
          <input
            type="text"
            className="form-input"
            placeholder="Search by title or description..."
            value={filters.search || ''}
            onChange={(e) => onFilterChange({ ...filters, search: e.target.value })}
          />
        </div>

        {/* Status Filter */}
        <div style={{ minWidth: '150px' }}>
          <select
            className="form-select"
            value={filters.status || ''}
            onChange={(e) => onFilterChange({ ...filters, status: e.target.value || undefined })}
          >
            <option value="">All Statuses</option>
            <option value="todo">To Do</option>
            <option value="in_progress">In Progress</option>
            <option value="review">Review</option>
            <option value="done">Completed</option>
          </select>
        </div>

        {/* Priority Filter */}
        <div style={{ minWidth: '150px' }}>
          <select
            className="form-select"
            value={filters.priority || ''}
            onChange={(e) => onFilterChange({ ...filters, priority: e.target.value || undefined })}
          >
            <option value="">All Priorities</option>
            <option value="urgent">Urgent</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>

        {/* Project Filter */}
        <div style={{ minWidth: '180px' }}>
          <select
            className="form-select"
            value={filters.project_id || ''}
            onChange={(e) => onFilterChange({ ...filters, project_id: e.target.value ? Number(e.target.value) : '' })}
          >
            <option value="">All Projects</option>
            {projects.map((p) => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        {(filters.status || filters.priority || filters.project_id || filters.search) && (
          <Button
            variant="ghost"
            style={{ fontSize: '0.825rem' }}
            onClick={() => onFilterChange({ status: undefined, priority: undefined, project_id: '', search: '' })}
          >
            Clear Filters
          </Button>
        )}
      </div>

      {/* Task Grid */}
      {tasks.length === 0 ? (
        <EmptyState
          title="No Tasks Found"
          description="No tasks match the active filters. Try adjusting search criteria or create a new task."
          actionText="Create Task"
          onAction={onOpenCreateTask}
          icon="📝"
        />
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '1.25rem' }}>
          {tasks.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              onSelect={onSelectTask}
              onQuickStatusChange={onQuickStatusChange}
            />
          ))}
        </div>
      )}
    </div>
  );
};
