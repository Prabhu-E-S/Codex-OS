import React, { useState } from 'react';
import { Task, User, Comment } from '../types';
import { Badge } from './common/Badge';
import { Button } from './common/Button';

interface TaskDetailModalProps {
  task: Task;
  users: User[];
  onClose: () => void;
  onEdit: (task: Task) => void;
  onDelete: (taskId: number) => Promise<void>;
  onStatusChange: (taskId: number, status: Task['status']) => Promise<void>;
  onAddComment: (taskId: number, content: string, authorId: number) => Promise<Comment>;
}

export const TaskDetailModal: React.FC<TaskDetailModalProps> = ({
  task,
  users,
  onClose,
  onEdit,
  onDelete,
  onStatusChange,
  onAddComment,
}) => {
  const [commentText, setCommentText] = useState('');
  const [authorId, setAuthorId] = useState<number | ''>(users[0]?.id || '');
  const [isSubmittingComment, setIsSubmittingComment] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [commentError, setCommentError] = useState<string | null>(null);

  const handleCommentSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentText.trim()) return;
    if (!authorId) {
      setCommentError('Please select a commenter.');
      return;
    }

    try {
      setIsSubmittingComment(true);
      setCommentError(null);
      await onAddComment(task.id, commentText.trim(), Number(authorId));
      setCommentText('');
    } catch (err: unknown) {
      setCommentError(err instanceof Error ? err.message : 'Failed to post comment.');
    } finally {
      setIsSubmittingComment(false);
    }
  };

  const handleDelete = async () => {
    if (window.confirm(`Delete task "${task.title}"?`)) {
      try {
        setIsDeleting(true);
        await onDelete(task.id);
        onClose();
      } finally {
        setIsDeleting(false);
      }
    }
  };

  const formattedDueDate = task.due_date
    ? new Date(task.due_date).toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    : null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()} style={{ maxWidth: '680px' }}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
            <Badge type="priority" value={task.priority} />
            <Badge type="status" value={task.status} />
            {task.is_overdue && <Badge type="overdue" value="overdue" />}
          </div>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        {/* Task Title & Project */}
        <div style={{ marginBottom: '1.5rem' }}>
          <h2 style={{ fontSize: '1.35rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '0.4rem' }}>
            {task.title}
          </h2>
          {task.project_name && (
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>
              Project: <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{task.project_name}</span>
            </p>
          )}
        </div>

        {/* Description */}
        <div style={{ marginBottom: '1.5rem', background: 'var(--bg-card)', padding: '1rem', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
          <h4 style={{ fontSize: '0.8rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
            Description
          </h4>
          <p style={{ color: 'var(--text-primary)', fontSize: '0.925rem', lineHeight: '1.6', whiteSpace: 'pre-line' }}>
            {task.description || 'No description provided.'}
          </p>
        </div>

        {/* Meta Info Grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem', marginBottom: '1.5rem' }}>
          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Assignee</span>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: 'var(--text-primary)' }}>
              {task.assignee ? task.assignee.full_name : 'Unassigned'}
            </span>
          </div>

          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Due Date</span>
            <span style={{ fontSize: '0.875rem', fontWeight: 600, color: task.is_overdue ? '#fca5a5' : 'var(--text-primary)' }}>
              {formattedDueDate || 'No due date'}
            </span>
          </div>

          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: 'var(--radius-md)' }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'block' }}>Quick Status</span>
            <select
              value={task.status}
              onChange={(e) => onStatusChange(task.id, e.target.value as Task['status'])}
              style={{
                background: 'transparent',
                border: 'none',
                color: 'var(--text-primary)',
                fontWeight: 600,
                fontSize: '0.875rem',
                cursor: 'pointer',
                outline: 'none',
                width: '100%'
              }}
            >
              <option value="todo">To Do</option>
              <option value="in_progress">In Progress</option>
              <option value="review">Review</option>
              <option value="done">Done</option>
            </select>
          </div>
        </div>

        {/* Comments Section */}
        <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '1.5rem', marginBottom: '1.5rem' }}>
          <h3 style={{ fontSize: '1.05rem', fontWeight: 700, marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <span>Comments</span>
            <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>({task.comments?.length || 0})</span>
          </h3>

          {/* Comment list */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: '220px', overflowY: 'auto', marginBottom: '1rem' }}>
            {(!task.comments || task.comments.length === 0) ? (
              <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', fontStyle: 'italic' }}>
                No comments yet. Start the conversation!
              </p>
            ) : (
              task.comments.map((comment) => (
                <div
                  key={comment.id}
                  style={{
                    background: 'var(--bg-card-hover)',
                    border: '1px solid var(--border-subtle)',
                    borderRadius: 'var(--radius-md)',
                    padding: '0.75rem 1rem',
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
                    <span style={{ fontWeight: 600, fontSize: '0.825rem', color: 'var(--accent-blue)' }}>
                      {comment.author?.full_name || `User #${comment.author_id}`}
                    </span>
                    <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                      {new Date(comment.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  <p style={{ fontSize: '0.875rem', color: 'var(--text-primary)', lineHeight: '1.5' }}>
                    {comment.content}
                  </p>
                </div>
              ))
            )}
          </div>

          {/* Add comment form */}
          <form onSubmit={handleCommentSubmit}>
            {commentError && (
              <div style={{ color: '#f87171', fontSize: '0.8rem', marginBottom: '0.5rem' }}>{commentError}</div>
            )}
            <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <input
                type="text"
                className="form-input"
                placeholder="Write a comment..."
                value={commentText}
                onChange={(e) => setCommentText(e.target.value)}
              />
              <select
                className="form-select"
                style={{ width: '160px' }}
                value={authorId}
                onChange={(e) => setAuthorId(e.target.value ? Number(e.target.value) : '')}
              >
                {users.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
              <Button type="submit" isLoading={isSubmittingComment} disabled={!commentText.trim()}>
                Post
              </Button>
            </div>
          </form>
        </div>

        {/* Modal Actions */}
        <div style={{ display: 'flex', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: '1rem' }}>
          <Button variant="danger" isLoading={isDeleting} onClick={handleDelete}>
            Delete Task
          </Button>

          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <Button variant="secondary" onClick={onClose}>
              Close
            </Button>
            <Button onClick={() => { onClose(); onEdit(task); }}>
              Edit Task
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
};
