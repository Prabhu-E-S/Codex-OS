# TaskForge REST API Documentation

Base URL: `http://localhost:8000/api/v1`  
Interactive OpenAPI / Swagger UI: `http://localhost:8000/docs`

---

## 1. System & Health

### `GET /health`
Returns system health status.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "taskforge-backend",
  "version": "1.0.0"
}
```

---

## 2. Dashboard

### `GET /api/v1/dashboard/stats`
Calculates high-level metrics, pending/overdue counts, and breakdown distributions.

**Response (200 OK):**
```json
{
  "total_projects": 3,
  "total_tasks": 7,
  "completed_tasks": 2,
  "pending_tasks": 5,
  "overdue_tasks": 2,
  "tasks_by_priority": {
    "low": 1,
    "medium": 1,
    "high": 3,
    "urgent": 2
  },
  "tasks_by_status": {
    "todo": 3,
    "in_progress": 2,
    "review": 0,
    "done": 2
  },
  "recent_tasks": [...],
  "recent_projects": [...]
}
```

---

## 3. Projects

### `POST /api/v1/projects`
Creates a new project.

**Request Body:**
```json
{
  "name": "Platform Scaling",
  "description": "Optimize microservices latency",
  "status": "active",
  "owner_id": 1
}
```

### `GET /api/v1/projects`
Lists all projects with their task count.

### `GET /api/v1/projects/{project_id}`
Returns details for a project including owner info and task count.

### `PATCH /api/v1/projects/{project_id}`
Updates project attributes (`name`, `description`, `status`, `owner_id`).

### `DELETE /api/v1/projects/{project_id}`
Deletes a project and cascades deletion to all associated tasks and comments. Returns `204 No Content`.

---

## 4. Tasks

### `POST /api/v1/tasks`
Creates a new task.

**Request Body:**
```json
{
  "title": "Configure Redis Cache",
  "description": "Cache frequently queried dashboard metrics",
  "status": "todo",
  "priority": "high",
  "due_date": "2026-09-30T12:00:00Z",
  "project_id": 1,
  "assignee_id": 2
}
```

### `GET /api/v1/tasks`
Lists tasks with multi-field filtering.

**Query Parameters:**
- `status`: `todo` | `in_progress` | `review` | `done`
- `priority`: `low` | `medium` | `high` | `urgent`
- `project_id`: integer
- `assignee_id`: integer
- `search`: string (case-insensitive substring match in title and description)
- `skip`: integer (default 0)
- `limit`: integer (default 100)

### `GET /api/v1/tasks/{task_id}`
Returns full task details including embedded comments and author info.

### `PATCH /api/v1/tasks/{task_id}`
Updates task status, priority, title, description, or assignee.

### `DELETE /api/v1/tasks/{task_id}`
Deletes task and associated comments. Returns `204 No Content`.

---

## 5. Comments

### `POST /api/v1/tasks/{task_id}/comments`
Adds a comment to a specific task.

**Request Body:**
```json
{
  "content": "Load testing indicates 40% query latency reduction.",
  "author_id": 1
}
```

### `GET /api/v1/tasks/{task_id}/comments`
Returns all comments posted to a task ordered by time.

---

## 6. Users

### `POST /api/v1/users`
Registers a new team member.

**Request Body:**
```json
{
  "email": "developer@example.com",
  "full_name": "Dev User",
  "role": "member",
  "is_active": true
}
```

### `GET /api/v1/users`
Lists all active users.

### `GET /api/v1/users/{user_id}`
Retrieves a user by their primary key.

### `PATCH /api/v1/users/{user_id}`
Updates user details.
